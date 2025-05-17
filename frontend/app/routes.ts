import Home from "./pages/Home";
import Welcome from "./pages/Welcome";
import Wizard from "./pages/Wizard";

export default [
  {
    path: "/",
    element: Home,
    file: "./pages/Home.tsx",
  },
  {
    path: "/welcome", 
    element: Welcome,
    file: "./pages/Welcome.tsx",
  },
  {
    path: "/wizard",
    element: Wizard,
    file: "./pages/Wizard.tsx",
  },
];
