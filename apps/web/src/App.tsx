import { type ReactNode, useEffect, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { token } from './api/client'; import { AppLayout } from './layouts/AppLayout';
import { EnvironmentsPage } from './pages/admin/EnvironmentsPage'; import { FormBuilderPage } from './pages/admin/FormBuilderPage'; import { UsersPage } from './pages/admin/UsersPage';
import { LoginPage } from './pages/auth/LoginPage'; import { RegisterPage } from './pages/auth/RegisterPage';
import { CaseDetailsPage } from './pages/cases/CaseDetailsPage'; import { CreateCasePage } from './pages/cases/CreateCasePage';
import { DashboardPage } from './pages/dashboard/DashboardPage'; import { CaseReportPage } from './pages/reports/cases/CaseReportPage';
import { PermissionsPage } from './pages/admin/permissions/PermissionsPage';
import { PendingApprovalsPage } from './pages/approvals/PendingApprovalsPage';
import { UserFieldsPage } from './pages/admin/user-fields/UserFieldsPage';
import { ReportsCenterPage } from './pages/reports/ReportsCenterPage';
import { ApprovalReportPage } from './pages/reports/ApprovalReportPage'; import { UsersPermissionsReportPage } from './pages/reports/UsersPermissionsReportPage'; import { AuditReportPage } from './pages/reports/AuditReportPage';
import { AppErrorBoundary } from './components/AppErrorBoundary';
import { GlobalFieldsPage } from './pages/admin/GlobalFieldsPage';
import { ImplementerStudioPage } from './pages/implementer/ImplementerStudioPage';
import { CapabilityGuard } from './components/CapabilityGuard';
import { PortalHomePage } from './pages/portal/PortalHomePage';
import { SlaReportPage } from './pages/reports/SlaReportPage';
function Authenticated({children}:{children:ReactNode}){const[authenticated,setAuthenticated]=useState(Boolean(token.get()));useEffect(()=>{const update=()=>setAuthenticated(Boolean(token.get()));window.addEventListener('case-management-auth',update);return()=>window.removeEventListener('case-management-auth',update)},[]);return authenticated?children:<Navigate to="/login" replace/>}
export default function App(){return <AppErrorBoundary><Routes><Route path="/login" element={<LoginPage/>}/><Route path="/register" element={<RegisterPage/>}/><Route element={<Authenticated><AppLayout/></Authenticated>}><Route path="/" element={<PortalHomePage/>}/><Route path="/portal" element={<PortalHomePage/>}/><Route path="/workspace" element={<DashboardPage/>}/><Route path="/cases" element={<Navigate to="/workspace?tab=my" replace/>}/><Route path="/assigned" element={<Navigate to="/workspace?tab=assigned" replace/>}/><Route path="/approvals/pending" element={<PendingApprovalsPage/>}/><Route path="/cases/new" element={<CreateCasePage/>}/><Route path="/cases/:id" element={<CaseDetailsPage/>}/><Route path="/implementer" element={<CapabilityGuard><ImplementerStudioPage/></CapabilityGuard>}/><Route path="/admin/environments" element={<CapabilityGuard><EnvironmentsPage/></CapabilityGuard>}/><Route path="/admin/request-types/:id" element={<CapabilityGuard><FormBuilderPage/></CapabilityGuard>}/><Route path="/admin/users" element={<CapabilityGuard><UsersPage/></CapabilityGuard>}/><Route path="/admin/user-fields" element={<CapabilityGuard><UserFieldsPage/></CapabilityGuard>}/><Route path="/admin/permissions" element={<CapabilityGuard><PermissionsPage/></CapabilityGuard>}/><Route path="/admin/case-values" element={<CapabilityGuard><GlobalFieldsPage/></CapabilityGuard>}/><Route path="/reports" element={<ReportsCenterPage/>}/><Route path="/reports/cases" element={<CaseReportPage/>}/><Route path="/reports/approvals" element={<ApprovalReportPage/>}/><Route path="/reports/users" element={<UsersPermissionsReportPage/>}/><Route path="/reports/audit" element={<AuditReportPage/>}/><Route path="/reports/sla" element={<SlaReportPage/>}/></Route></Routes></AppErrorBoundary>}
