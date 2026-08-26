import { createBrowserRouter } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { About } from "@/pages/About";
import { Attempt } from "@/pages/Attempt";
import { Contact } from "@/pages/Contact";
import { Dashboard } from "@/pages/Dashboard";
import { Home } from "@/pages/Home";
import { Login } from "@/pages/Login";
import { Articles, History, NotFound } from "@/pages/Misc";
import { ModulePage } from "@/pages/ModulePage";
import { Practice } from "@/pages/Practice";
import { Profile } from "@/pages/Profile";
import { Register } from "@/pages/Register";
import { Result } from "@/pages/Result";
import { Revision } from "@/pages/Revision";
import { ServiceHub } from "@/pages/ServiceHub";
import { Services } from "@/pages/Services";
import { Tests } from "@/pages/Tests";
import { AdminArticles } from "@/pages/admin/Articles";
import { AdminHome } from "@/pages/admin/AdminHome";
import { AdminUsers } from "@/pages/admin/Users";
import { Generate } from "@/pages/admin/Generate";
import { Maintenance } from "@/pages/admin/Maintenance";
import { QuestionBank } from "@/pages/admin/QuestionBank";
import { ReviewQueue } from "@/pages/admin/ReviewQueue";
import { GtoTask, GtoTasks } from "@/pages/issb/Gto";
import { Interview } from "@/pages/issb/Interview";
import { InterviewResult } from "@/pages/issb/InterviewResult";
import { IssbHub } from "@/pages/issb/IssbHub";
import { OlqProfilePage } from "@/pages/issb/OlqProfilePage";
import { PsychResult } from "@/pages/issb/PsychResult";
import { PsychRunner } from "@/pages/issb/PsychRunner";
import { Ppdt } from "@/pages/issb/Ppdt";
import { PrintSheet } from "@/pages/issb/PrintSheet";
import { SheetUpload } from "@/pages/issb/SheetUpload";

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      // --- Public ---------------------------------------------------------
      { path: "/", element: <Home /> },
      { path: "/login", element: <Login /> },
      { path: "/register", element: <Register /> },
      { path: "/services", element: <Services /> },
      { path: "/services/:code", element: <ServiceHub /> },
      { path: "/modules/:id", element: <ModulePage /> },
      { path: "/articles", element: <Articles /> },
      { path: "/about", element: <About /> },
      { path: "/contact", element: <Contact /> },

      // --- Signed in ------------------------------------------------------
      {
        element: <ProtectedRoute />,
        children: [
          { path: "/dashboard", element: <Dashboard /> },
          { path: "/practice", element: <Practice /> },
          { path: "/tests", element: <Tests /> },
          { path: "/revision", element: <Revision /> },
          { path: "/history", element: <History /> },
          { path: "/profile", element: <Profile /> },

          // The paper and its result: both meaningless without a session.
          { path: "/attempts/:id", element: <Attempt /> },
          { path: "/attempts/:id/result", element: <Result /> },

          // ISSB simulation suite.
          { path: "/issb", element: <IssbHub /> },
          { path: "/issb/psych/:test", element: <PsychRunner /> },
          { path: "/issb/psych/result/:id", element: <PsychResult /> },
          { path: "/issb/gto", element: <GtoTasks /> },
          { path: "/issb/gto/:id", element: <GtoTask /> },
          { path: "/issb/interview", element: <Interview /> },
          { path: "/issb/interview/result/:id", element: <InterviewResult /> },
          { path: "/issb/profile", element: <OlqProfilePage /> },
          { path: "/issb/ppdt", element: <Ppdt /> },
          // Practise on paper, then photograph it: two halves of one loop.
          { path: "/issb/sheet", element: <PrintSheet /> },
          { path: "/issb/upload", element: <SheetUpload /> },
        ],
      },

      // --- Staff ----------------------------------------------------------
      // Gated in the UI, and independently enforced by the API.
      {
        element: <ProtectedRoute staffOnly />,
        children: [
          { path: "/admin", element: <AdminHome /> },
          { path: "/admin/generate", element: <Generate /> },
          { path: "/admin/queue", element: <ReviewQueue /> },
          { path: "/admin/questions", element: <QuestionBank /> },
          { path: "/admin/articles", element: <AdminArticles /> },
          { path: "/admin/users", element: <AdminUsers /> },
          { path: "/admin/maintenance", element: <Maintenance /> },
        ],
      },

      { path: "*", element: <NotFound /> },
    ],
  },
]);
