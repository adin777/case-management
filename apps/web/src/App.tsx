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
import { ReportsCenterPage } from './pages/reports/ReportsCenterPage'; import { SimpleReportPage } from './pages/reports/SimpleReportPage';
function Authenticated({children}:{children:ReactNode}){const[authenticated,setAuthenticated]=useState(Boolean(token.get()));useEffect(()=>{const update=()=>setAuthenticated(Boolean(token.get()));window.addEventListener('case-management-auth',update);return()=>window.removeEventListener('case-management-auth',update)},[]);return authenticated?children:<Navigate to="/login" replace/>}
export default function App(){return <Routes><Route path="/login" element={<LoginPage/>}/><Route path="/register" element={<RegisterPage/>}/><Route element={<Authenticated><AppLayout/></Authenticated>}><Route path="/" element={<DashboardPage/>}/><Route path="/cases" element={<Navigate to="/?tab=my" replace/>}/><Route path="/assigned" element={<Navigate to="/?tab=assigned" replace/>}/><Route path="/approvals/pending" element={<PendingApprovalsPage/>}/><Route path="/cases/new" element={<CreateCasePage/>}/><Route path="/cases/:id" element={<CaseDetailsPage/>}/><Route path="/admin/environments" element={<EnvironmentsPage/>}/><Route path="/admin/request-types/:id" element={<FormBuilderPage/>}/><Route path="/admin/users" element={<UsersPage/>}/><Route path="/admin/user-fields" element={<UserFieldsPage/>}/><Route path="/admin/permissions" element={<PermissionsPage/>}/><Route path="/reports" element={<ReportsCenterPage/>}/><Route path="/reports/cases" element={<CaseReportPage/>}/><Route path="/reports/:kind" element={<SimpleReportPage/>}/></Route></Routes>}
