# Fan-out / Fan-in (Durable Functions)

This README explains the Fan-out / Fan-in orchestration pattern and shows how to implement it using Azure Durable Functions (Python). The project in this workspace is an Azure Functions app that can use this pattern to process multiple inputs concurrently and then aggregate results.

**What is Fan-out / Fan-in?**

- **Fan-out:** split a larger work item into many smaller, independent tasks and run them in parallel.
- **Fan-in:** wait for all parallel tasks to finish and then aggregate or process the combined results.

This pattern is useful when you can perform work independently (parallelizable), e.g., calling multiple APIs, processing files, or running computations for many items.

**How it works (high level)**

1. Orchestrator receives an array of inputs.
2. Orchestrator starts an activity function for each input (the fan-out step), collecting a list of task handles.
3. Orchestrator waits for all tasks to complete (fan-in), commonly using a Task/await-all helper.
4. Orchestrator aggregates the results and returns or persists the final outcome.

**Durable Functions (Python) example from this project**

Here's the fan-out/fan-in pattern from `function_app.py`:

**Orchestrator function:**

```python
@myApp.orchestration_trigger(context_name="context")
def hello_orchestrator(context):
    # Single task execution
    result1 = yield context.call_activity("hello", "Seattle")

    # Fan-out: create a list of parallel tasks (one for each city)
    list_cities_morocco = ["Casablanca", "Marrakesh", "Fes"]
    parallel_tasks = [context.call_activity("print_message_and_wait_random", city) for city in list_cities_morocco]

    # Fan-in: wait for all parallel tasks to complete
    results_morocco = yield context.task_all(parallel_tasks)
    context.set_custom_status("Completed Seattle, starting Morocco cities...")

    logger.info(f"Completed greetings for Morocco cities: {','.join(results_morocco)}")

    # More sequential tasks after fan-in completes
    result2 = yield context.call_activity("hello", "Tokyo")
    result3 = yield context.call_activity("hello", "London")

    return [result1, results_morocco, result2, result3]
```

**Activity functions:**

```python
@myApp.activity_trigger(input_name="city")
def hello(city: str):
    return f"Hello {city}"

@myApp.activity_trigger(input_name="message")
def print_message_and_wait_random(message: str):
    import random
    import time

    logger.debug(message)
    wait_time = random.randint(1, 5)
    time.sleep(wait_time)
    return f"Waited for {str(wait_time)} seconds after printing message."
```

**How it works in this example:**

1. **Sequential start:** Process "Seattle" first.
2. **Fan-out:** Create three parallel tasks (one per Morocco city: Casablanca, Marrakesh, Fes).
3. **Fan-in:** `context.task_all(parallel_tasks)` waits for all three tasks to finish and collects results in `results_morocco`.
4. **Sequential end:** After all Morocco tasks complete, process "Tokyo" and "London" sequentially.
5. **Return:** Aggregate all results and return them.

**Key points:**

- `context.call_activity()` returns a task that the orchestrator can yield.
- `context.task_all()` waits for all tasks in the list to complete (fan-in).
- The pattern allows independent work to run in parallel, then synchronize at a checkpoint.

**Retries and Error Handling**

- Use retries for transient failures: create retry options and call `call_activity_with_retry`.
- Consider wrapping critical aggregations with try/except in a separate activity, or implement compensating actions if any child fails.

Example with retry:

```python
from azure.durable_functions.models import RetryOptions

retry_options = RetryOptions(first_retry_interval_in_milliseconds=5000, max_number_of_attempts=3)

for item in items:
    tasks.append(context.call_activity_with_retry('ProcessItem', retry_options, item))
```

**Best practices & considerations**

- Make activities idempotent. Orchestrations may replay and activities could be retried.
- Keep activity payloads small; pass references (URIs, blob names) instead of large blobs when possible.
- Watch orchestration history size — storing huge results in the orchestration context can cause performance issues.
- Use sub-orchestrations for large chains of work to keep orchestration history manageable.
- Respect parallelism limits of downstream services (throttle if necessary).

**Local testing / Run commands**

From this project root, you can run locally with the Azure Functions Core Tools.

Install dependencies (if not already installed):

```bash
# macOS / zsh example
python -m pip install -r requirements.txt
```

Start the Functions host:

```bash
func host start
```

Trigger your orchestration using an HTTP starter function or the Azure Storage queue/topic you have configured in this project. Example (HTTP start): POST to the orchestration starter endpoint with JSON body `[1,2,3]`.

**When to use this pattern**

- Use when independent work items can safely run in parallel and you need to combine results.
- Avoid when steps have heavy cross-dependencies or require strict sequential ordering.

# Logging in Azure Durable Functions (Python)

## Quick Setup

### host.json

```json
{
  "version": "2.0",
  "logging": {
    "logLevel": {
      "default": "Information",
      "Host.Results": "Information",
      "Function": "Information",
      "Function.<FUNCTION_NAME>.User": "Information"
    }
  }
}
```

### Python Code

```python
import logging

logger = logging.getLogger("azure.functions")

@myApp.activity_trigger(input_name="message")
def my_activity(message: str):
    logger.info(f"Processing: {message}")  # ✅ Use f-string
    # logger.info("Processing: %s", message)  # ✅ Or use %s placeholder
    # logger.info("Message:", message)  # ❌ Causes formatting error
    return "Done"
```

## Common Mistakes

| ❌ Wrong                   | ✅ Correct                                                    |
| -------------------------- | ------------------------------------------------------------- |
| `logging.basicConfig()`    | Remove it - interferes with Azure Functions                   |
| `logging.info("msg", var)` | `logging.info(f"msg {var}")` or `logging.info("msg %s", var)` |
| Logging in orchestrators   | Use `context.set_custom_status()` instead                     |

## Log Levels

| Level         | Code | Use Case                                                        |
| ------------- | ---- | --------------------------------------------------------------- |
| `Trace`       | 0    | Most detailed, may contain sensitive data - never in production |
| `Debug`       | 1    | Development debugging, no long-term value                       |
| `Information` | 2    | General flow tracking, long-term value                          |
| `Warning`     | 3    | Unexpected but non-breaking events                              |
| `Error`       | 4    | Failures that stop current execution                            |
| `Critical`    | 5    | Unrecoverable crashes requiring immediate attention             |
| `None`        | 6    | Disables logging for the category                               |

## Enable Logging Per Function

### Basic: Enable for All Functions

```json
{
  "version": "2.0",
  "logging": {
    "logLevel": {
      "default": "Warning",
      "Function": "Information"
    }
  }
}
```

### Advanced: Enable for Specific Function

```json
{
  "version": "2.0",
  "logging": {
    "logLevel": {
      "default": "Warning",
      "Function": "Error",
      "Function.my_activity": "Information",
      "Function.my_activity.User": "Information"
    }
  }
}
```

This configuration:

- Sets default to `Warning` (reduces noise)
- Sets all functions to `Error` (only errors logged)
- Enables `Information` level for `my_activity` function specifically
- Enables user logs (your `logger.info()` calls) for `my_activity`

### Override at Runtime (Without Redeployment)

Use app settings with format `AzureFunctionsJobHost__path__to__setting`:

```bash
# Azure CLI
az functionapp config appsettings set \
  --name MyFunctionApp \
  --resource-group MyResourceGroup \
  --settings "AzureFunctionsJobHost__logging__logLevel__Function.my_activity=Debug"
```

| host.json Path                      | App Setting                                                  |
| ----------------------------------- | ------------------------------------------------------------ |
| `logging.logLevel.default`          | `AzureFunctionsJobHost__logging__logLevel__default`          |
| `logging.logLevel.Function`         | `AzureFunctionsJobHost__logging__logLevel__Function`         |
| `logging.logLevel.Function.my_func` | `AzureFunctionsJobHost__logging__logLevel__Function.my_func` |

## Production Recommended Configuration

```json
{
  "version": "2.0",
  "logging": {
    "logLevel": {
      "default": "Warning",
      "Host.Aggregator": "Information",
      "Host.Results": "Information",
      "Function": "Warning",
      "Function.critical_function": "Information",
      "Function.critical_function.User": "Information"
    },
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "maxTelemetryItemsPerSecond": 20,
        "excludedTypes": "Exception"
      }
    }
  }
}
```

## Key Categories

- `Function` - Function started/completed logs
- `Function.<NAME>.User` - Your custom logs inside functions
- `Host.Results` - Success/failure of invocations
- `Host.Aggregator` - Aggregated metrics

## References

- [Configure Monitoring](https://learn.microsoft.com/en-us/azure/azure-functions/configure-monitoring)
- [Durable Functions Docs](https://learn.microsoft.com/en-us/azure/azure-functions/durable/)
- Durable Functions patterns — Fan-out/Fan-in: https://learn.microsoft.com/azure/azure-functions/durable/durable-functions-concepts#fan-out---fan-in
- Durable Functions (Python) overview: https://learn.microsoft.com/azure/azure-functions/durable/durable-functions-python
