"""Local ETL review interface. Run with python app.py."""
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from src.backend.pipeline import Workflow


def main():
    workflow = Workflow()
    root = tk.Tk()
    root.title("CIEH ETL — upload and review")
    root.geometry("1100x650")
    events = queue.Queue()
    current = [None]
    format_var = tk.StringVar(value=".csv")
    status = tk.StringVar(value="Upload a file or resume a pending review.")
    toolbar = ttk.Frame(root)
    toolbar.pack(fill="x")
    ttk.Label(toolbar, text="File format:").pack(side="left")
    ttk.Combobox(toolbar, textvariable=format_var, values=workflow.config["files"]["extensions"], state="readonly", width=10).pack(side="left")
    table = ttk.Treeview(root, columns=workflow.config["master"]["columns"], show="headings")
    for column in table["columns"]:
        table.heading(column, text=column)
        table.column(column, width=140)
    scrollbar = ttk.Scrollbar(root, orient="horizontal", command=table.xview)
    table.configure(xscrollcommand=scrollbar.set)
    table.pack(fill="both", expand=True)
    scrollbar.pack(fill="x")
    ttk.Label(root, textvariable=status).pack(fill="x")

    def show(job):
        current[0] = job
        table.delete(*table.get_children())
        for row in job["records"]:
            table.insert("", "end", values=["null" if row[c] is None else str(row[c]) for c in table["columns"]])
        status.set(f"{job['filename']}: {len(job['records'])} records. Review before accepting.")
        accept_button.config(state="normal")
        discard_button.config(state="normal" if job["status"] == "pending" else "disabled")

    def resume():
        jobs = workflow.pending()
        if jobs:
            show(jobs[0])
        else:
            status.set("No pending uploads. Choose a file to start.")

    def upload():
        path = filedialog.askopenfilename()
        if not path:
            return
        selected_format = format_var.get()
        upload_button.config(state="disabled")
        accept_button.config(state="disabled")
        discard_button.config(state="disabled")
        status.set("Parsing and matching columns…")
        def work():
            try:
                events.put((True, workflow.process(path, selected_format)))
            except Exception as error:
                events.put((False, str(error)))
        threading.Thread(target=work, daemon=True).start()

    def poll():
        try:
            ok, result = events.get_nowait()
            upload_button.config(state="normal")
            if ok:
                show(result)
            else:
                status.set("Processing failed. The source file is preserved.")
                messagebox.showerror("Processing failed", result)
                resume()
        except queue.Empty:
            pass
        root.after(150, poll)

    def decide(accept):
        try:
            workflow.decide(current[0]["id"], accept)
            current[0] = None
            table.delete(*table.get_children())
            accept_button.config(state="disabled")
            discard_button.config(state="disabled")
            status.set("Accepted and merged into master." if accept else "Discarded; master unchanged.")
            if workflow.pending():
                resume()
        except Exception as error:
            messagebox.showerror("Review failed", str(error))

    upload_button = ttk.Button(toolbar, text="Upload and process", command=upload)
    upload_button.pack(side="left")
    ttk.Button(toolbar, text="Resume pending review", command=resume).pack(side="left")
    accept_button = ttk.Button(toolbar, text="Accept and merge", command=lambda: decide(True), state="disabled")
    accept_button.pack(side="left")
    discard_button = ttk.Button(toolbar, text="Discard", command=lambda: decide(False), state="disabled")
    discard_button.pack(side="left")
    resume()
    poll()
    root.mainloop()


if __name__ == "__main__":
    main()
