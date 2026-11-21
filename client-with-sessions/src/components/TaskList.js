import { useEffect, useState } from "react";

/**
 * Display tasks belonging to the authenticated user.
 *
 * Fetches paginated task data from the Flask API and
 * handles loading, errors, empty results, and navigation.
 */
function TaskList() {
    // Store the tasks returned by the API
  const [tasks, setTasks] = useState([]);

  // Track the current page and total available pages
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // Track request status for conditional rendering
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  /**
   * Fetch the current page of tasks.
   *
   * Runs when the component mounts and whenever the
   * page state changes.
   */
  useEffect(() => {
    setLoading(true);
    setError("");

    // Request five tasks per page from the Flask API
    fetch(`/tasks?page=${page}&per_page=5`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Unable to load tasks");
        }

        return response.json();
      })
      .then((data) => {
        // Update the task list and pagination metadata
        setTasks(data.items);
        setTotalPages(data.total_pages);
      })
      .catch((err) => {
        // Display a message if the request fails
        setError(err.message);
      })
      .finally(() => {
        // End the loading state regardless of the outcome
        setLoading(false);
      });
  }, [page]);

  // Display a loading message while requesting tasks
  if (loading) {
    return <p>Loading tasks...</p>;
  }

  // Display an error message if the request fails
  if (error) {
    return <p>{error}</p>;
  }

  return (
    <div>
      <h2>My Tasks</h2>

      {/* Display an empty state or the user's tasks */}
      {tasks.length === 0 ? (
        <p>No tasks found.</p>
      ) : (
        <ul>
          {tasks.map((task) => (
            <li key={task.id}>
              <h3>{task.title}</h3>

              <p>Status: {task.status}</p>
              <p>Priority: {task.priority}</p>
              <p>{task.description}</p>
            </li>
          ))}
        </ul>
      )}

    {/* Hide pagination when no pages are available */}
    {totalPages > 0 && (
      <div>
        <button
          disabled={page === 1}
          onClick={() => setPage(page - 1)}
        >
          Previous
        </button>

        <span> Page {page} of {totalPages} </span>

        <button
          disabled={page >= totalPages}
          onClick={() => setPage(page + 1)}
        >
          Next
        </button>
      </div>
    )}

    </div>
  );
}

export default TaskList;