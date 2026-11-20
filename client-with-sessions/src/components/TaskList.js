import { useEffect, useState } from "react";

function TaskList() {
  const [tasks, setTasks] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");

    fetch(`/tasks?page=${page}&per_page=5`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Unable to load tasks");
        }

        return response.json();
      })
      .then((data) => {
        setTasks(data.items);
        setTotalPages(data.total_pages);
      })
      .catch((err) => {
        setError(err.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [page]);

  if (loading) {
    return <p>Loading tasks...</p>;
  }

  if (error) {
    return <p>{error}</p>;
  }

  return (
    <div>
      <h2>My Tasks</h2>

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
    </div>
  );
}

export default TaskList;