from flask import Flask, request, render_template_string, jsonify
import subprocess
import os

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Command Runner</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="container py-4">
    <h1 class="mb-4">🛠️ Shell Command Runner</h1>
    <form method="POST" class="mb-3">
        <div class="input-group mb-2">
            <input type="text" name="command" class="form-control" placeholder="Enter shell command..." required>
            <button class="btn btn-primary" type="submit">Run</button>
        </div>
        <div class="form-check mb-2">
            <input class="form-check-input" type="checkbox" name="background" id="background" {% if background %}checked{% endif %}>
            <label class="form-check-label" for="background">Run in background</label>
        </div>
    </form>

    {% if output %}
    <div class="mb-3">
        <label class="form-label">Output:</label>
        <textarea readonly class="form-control" rows="8">{{ output }}</textarea>
    </div>
    {% endif %}

    {% if background %}
    <form method="GET" class="mb-2">
        <button name="view_log" value="1" class="btn btn-secondary">Refresh output.log</button>
    </form>
    <div>
        <label class="form-label">Background Output (output.log):</label>
        <textarea readonly class="form-control" rows="8">{{ log_output }}</textarea>
    </div>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    output = ""
    log_output = ""
    background = False

    if request.method == "POST":
        command = request.form.get("command", "")
        background = request.form.get("background") == "on"

        if command.strip():
            if background:
                try:
                    subprocess.Popen(
                        f"nohup {command} > output.log 2>&1 &",
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    output = f"✅ Background job started for: `{command}`"
                except Exception as e:
                    output = f"❌ Background command failed: {e}"
            else:
                try:
                    result = subprocess.check_output(
                        command, shell=True, stderr=subprocess.STDOUT, text=True, timeout=30
                    )
                    output = result
                except subprocess.TimeoutExpired:
                    output = "❌ Command timed out after 30 seconds."
                except subprocess.CalledProcessError as e:
                    output = f"❌ Command failed:\n{e.output}"
                except Exception as e:
                    output = f"❌ Error: {e}"
        else:
            output = "⚠️ Please enter a valid command."

    # Show log if requested
    if request.method == "GET" and request.args.get("view_log") == "1":
        background = True
        try:
            with open("output.log", "r") as f:
                log_output = f.read()
        except FileNotFoundError:
            log_output = "output.log not found."

    return render_template_string(HTML_TEMPLATE, output=output, background=background, log_output=log_output)


@app.route("/api/run", methods=["POST"])
def run_command_api():
    data = request.get_json(force=True)
    command = data.get("command")
    background = data.get("background", False)

    if not command or not isinstance(command, str):
        return jsonify({"error": "Invalid or missing 'command' field"}), 400

    if background:
        try:
            subprocess.Popen(
                f"nohup {command} > output.log 2>&1 &",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return jsonify({"status": "started", "background": True, "message": f"Started `{command}`"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        try:
            result = subprocess.check_output(
                command, shell=True, stderr=subprocess.STDOUT, text=True, timeout=30
            )
            return jsonify({"status": "ok", "output": result})
        except subprocess.TimeoutExpired:
            return jsonify({"error": "Command timed out"}), 408
        except subprocess.CalledProcessError as e:
            return jsonify({"error": "Command failed", "output": e.output}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(debug=True, host="0.0.0.0", port=port)
