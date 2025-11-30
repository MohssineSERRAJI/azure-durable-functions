import azure.functions as func
import azure.durable_functions as df
import logging
import sys

logger = logging.getLogger("azure.functions")
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

myApp = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# An HTTP-triggered function with a Durable Functions client binding
@myApp.route(route="orchestrators/{functionName}")
@myApp.durable_client_input(client_name="client")
async def http_start(req: func.HttpRequest, client):
    function_name = req.route_params.get('functionName')
    instance_id = await client.start_new(function_name)
    response = client.create_check_status_response(req, instance_id)
    return response

# Orchestrator
@myApp.orchestration_trigger(context_name="context")
def hello_orchestrator(context):
    result1 = yield context.call_activity("hello", "Seattle")
    list_cities_morocco = ["Casablanca", "Marrakesh", "Fes"]
    parallel_tasks = [context.call_activity("print_message_and_wait_random", city) for city in list_cities_morocco]
    results_morocco = yield context.task_all(parallel_tasks)
    context.set_custom_status("Completed Seattle, starting Morocco cities...")

    logger.info(f"Completed greetings for Morocco cities: {','.join(results_morocco)}")
    print(f"Completed greetings for Morocco cities: {','.join(results_morocco)}")
    result2 = yield context.call_activity("hello", "Tokyo")
    result3 = yield context.call_activity("hello", "London")

    return [result1, results_morocco, result2, result3]

# Activity
@myApp.activity_trigger(input_name="city")
def hello(city: str):
    return f"Hello {city}"

# activity function with retry policy
@myApp.activity_trigger(input_name="message")
def print_message_and_wait_random(message: str):
    import random
    import time

    logger.debug(message)
    wait_time = random.randint(1, 5)
    time.sleep(wait_time)
    return f"Waited for {str(wait_time)} seconds after printing message."