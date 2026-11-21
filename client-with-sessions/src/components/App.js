import React, { useEffect, useState } from "react";
import NavBar from "./NavBar";
import Login from "../pages/Login";

// Import the custom component for displaying user tasks
import TaskList from "./TaskList";

function App() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    fetch("/check_session").then((r) => {
      if (r.ok) {
        r.json().then((user) => setUser(user));
      }
    });
  }, []);

  if (!user) return <Login onLogin={setUser} />;

  return (
    <>
      <NavBar user={user} setUser={setUser} />
      <main>
        <div>
          <h1>Welcome, {user.username}!</h1>

          {/* Display the authenticated user's paginated task list */}
          <TaskList />
        </div>
      </main>
    </>
  );
}

export default App;
