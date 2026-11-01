import { AppRouter } from "./routes";
import { AuthProvider } from "./context/AuthContext";
import { BusinessProvider } from "./context/BusinessContext";
import { ThemeProvider } from "./context/ThemeContext";

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BusinessProvider>
          <AppRouter />
        </BusinessProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
