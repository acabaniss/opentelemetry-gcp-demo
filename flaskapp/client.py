"""This simulates a client-side application."""

import requests
import time
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.cloud_trace_propagator import (
    CloudTraceFormatPropagator,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

set_global_textmap(CloudTraceFormatPropagator())

tracer_provider = TracerProvider()
cloud_trace_exporter = CloudTraceSpanExporter(project_id="ninth-moment-365704")
tracer_provider.add_span_processor(
    # BatchSpanProcessor buffers spans and sends them in batches in a
    # background thread. The default parameters are sensible, but can be
    # tweaked to optimize your performance
    BatchSpanProcessor(cloud_trace_exporter)
)
trace.set_tracer_provider(tracer_provider)

tracer = trace.get_tracer(__name__)

RequestsInstrumentor().instrument()

with tracer.start_as_current_span("request_roll") as reqspan:  
    res = requests.get("http://localhost:5000/rolldice")
    reqspan.set_attribute("roll.value.1", res.text)
    time.sleep(1)
    res = requests.get("http://localhost:5000/rolldice")
    reqspan.set_attribute("roll.value.2", res.text)
    reqspan.set_attribute("purpose","testing")
    
print(res.text)