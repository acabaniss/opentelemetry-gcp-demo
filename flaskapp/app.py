import os
from re import I
import time
from random import randint
from flask import Flask, request
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.cloud_trace_propagator import (
    CloudTraceFormatPropagator,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
import googlecloudprofiler



PROJECT_ID = os.environ.get('PROJECT_ID', "ninth-moment-365704")

counter = 0

# for logging
from google.cloud import logging as gclogging

logging_client = gclogging.Client(project=PROJECT_ID)
logger_name = "LOG_NAME_EXAMPLE"  # Saved in the google cloud logs
logger = logging_client.logger(logger_name)

# entry = gclogging.entries.StructEntry # not a real object
def write_log(span_context, message: str):
    trace_id = trace.format_trace_id(span_context.trace_id)
    span_id = trace.format_span_id(span_context.span_id)
    logger.log_struct(
        {
            "severity": "INFO",
            #"logging.googleapis.com/spanId": span_id,
            "span_id": span_id,
            #"logging.googleapis.com/trace": f"projects/{PROJECT_ID}/traces/{trace_id}",
            "trace": f"projects/{PROJECT_ID}/traces/{trace_id}",
            "message": message,
        }
    )


# Profiler initialization. It starts a daemon thread which continuously
# collects and uploads profiles. Best done as early as possible.
try:
    googlecloudprofiler.start(
        service=os.environ.get("K_SERVICE",'default'),
        service_version='0.1.2',
        # verbose is the logging level. 0-error, 1-warning, 2-info,
        # 3-debug. It defaults to 0 (error) if not set.
        verbose=3,
        # project_id must be set if not running on GCP.
        project_id=PROJECT_ID,
    )
except (ValueError, NotImplementedError) as exc:
    print(exc)  # Handle errors here

# For propagation
set_global_textmap(CloudTraceFormatPropagator())


tracer_provider = TracerProvider()
cloud_trace_exporter = CloudTraceSpanExporter(
    project_id=PROJECT_ID
)  # log testing project
tracer_provider.add_span_processor(
    # BatchSpanProcessor buffers spans and sends them in batches in a
    # background thread. The default parameters are sensible, but can be
    # tweaked to optimize your performance
    BatchSpanProcessor(cloud_trace_exporter)
)
trace.set_tracer_provider(tracer_provider)

# this  is alwas required
tracer = trace.get_tracer(__name__)

app = Flask(__name__)

# Instrument flask
FlaskInstrumentor().instrument_app(app)

def span_config():
    trace.get_current_span().set_attribute("run.service_name", os.environ.get("K_SERVICE",'unknown'))
    trace.get_current_span().set_attribute("run.service_revision", os.environ.get("K_REVISION",'unknown') )
    trace.get_current_span().set_attribute("run.service_configuration", os.environ.get("K_CONFIGURATION", 'unknown') )

@app.route("/")
def hello_world():
    span_config()
    time.sleep(1)
    name = os.environ.get("NAME", "World")

    write_log(trace.get_current_span().get_span_context(), f"Received name of {name}")
    return "Hello {}!".format(name)


# open telemetry route
@app.route("/rolldice")
def roll_dice():
    span_config()
    global counter 
    counter += 1
    trace.get_current_span().set_attribute("rolldice.callSeq", counter)
    if counter % 2 :
        return "I'm a Teapot", 418
    else:
        return str(do_roll())


def do_roll():
    with tracer.start_as_current_span("do_roll") as rollspan:
        res = randint(1, 6)
        rollspan.set_attribute("roll.value", res)
        write_log(
            trace.get_current_span().get_span_context(), f"Received dice roll of {res}"
        )
        return res


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
