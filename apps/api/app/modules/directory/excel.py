import io
import zipfile
from collections.abc import Sequence
from html import escape
from xml.etree import ElementTree

from pydantic import ValidationError

from app.modules.directory.provider import NormalizedDirectoryUser

USER_IMPORT_SCHEMA = (("First Name","first_name"),("Last Name","last_name"),("Display Name","display_name"),("Email","email"),("Username","user_principal_name"),("Department","department"),("Job Title","job_title"),("Phone","phone"),("Mobile Phone","mobile_phone"),("Employee ID","employee_id"),("Computer Identifier","computer_identifier"),("Active","directory_enabled"))
HEADERS=[column[0] for column in USER_IMPORT_SCHEMA];FIELDS=[column[1] for column in USER_IMPORT_SCHEMA]


def workbook(rows: Sequence[Sequence[object]], sheet_name: str = "Users") -> bytes:
    def cell(value: object) -> str: return f'<c t="inlineStr"><is><t>{escape(str(value or ""))}</t></is></c>'
    data = "".join(f'<row r="{i}">{"".join(cell(v) for v in row)}</row>' for i, row in enumerate(rows, 1))
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        archive.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        archive.writestr("xl/workbook.xml", f'<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets></workbook>')
        archive.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        archive.writestr("xl/worksheets/sheet1.xml", f'<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{data}</sheetData></worksheet>')
    return stream.getvalue()


def parse(content: bytes) -> list[NormalizedDirectoryUser]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            xml_root = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
        raise ValueError("קובץ Excel אינו תקין") from exc
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}; values: list[list[str]] = []
    for sheet_row in xml_root.findall(".//x:row", ns):
        values.append(["".join(cell.itertext()) for cell in sheet_row.findall("x:c", ns)])
    received = values[0] if values else []
    if received != HEADERS:
        missing = [header for header in HEADERS if header not in received]
        extra = [header for header in received if header not in HEADERS]
        raise ValueError(
            "כותרות הקובץ אינן תואמות לתבנית. "
            f"התקבלו: {received}; צפויות: {HEADERS}; חסרות: {missing}; עודפות: {extra}"
        )
    result = []
    for number, values_row in enumerate(values[1:], 2):
        padded = values_row + [""] * (len(FIELDS) - len(values_row)); data = dict(zip(FIELDS, padded, strict=True))
        if not data["email"]: raise ValueError(f"שורה {number}, Email: התקבל ערך ריק; צפויה כתובת דוא״ל תקינה; שדה חובה")
        data["display_name"] = data["display_name"] or f'{data["first_name"]} {data["last_name"]}'.strip()
        enabled = str(data["directory_enabled"]).strip().casefold() in {"true", "1", "yes", "כן", "active"}
        try: result.append(NormalizedDirectoryUser(
            first_name=data["first_name"] or None, last_name=data["last_name"] or None,
            display_name=str(data["display_name"]), email=str(data["email"]),
            user_principal_name=data["user_principal_name"] or None,
            department=data["department"] or None, job_title=data["job_title"] or None,
            phone=data["phone"] or None, mobile_phone=data["mobile_phone"] or None,
            employee_id=data["employee_id"] or None, computer_identifier=data["computer_identifier"] or None,
            directory_enabled=enabled,
        ))
        except ValidationError as exc:
            field=str(exc.errors()[0].get("loc",["value"])[0]);received_value=data.get(field,"");raise ValueError(f"שורה {number}, {field}: התקבל '{received_value}'; צפוי פורמט תקין; {exc.errors()[0]['msg']}") from exc
    return result
