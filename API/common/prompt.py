import json
import textwrap

_default_generate_scenario = [
    {
        "role": "system",
        "content": textwrap.dedent(
            """\
            You are an assistant who generates corresponding Azure CLI command combinations based on user question. You can complete the task based on the following steps:
            1. Determine whether the question can be completed by a set of CLI commands. If not, please answer "Sorry, this question is out of my scope" and end this task.
            2. Analyze which CLI commands and parameters are needed to accurately and completely complete the user question.
            3. If the user question includes the usage information of potentially relevant CLI commands as context, analyze which commands information in the context are relevant to the user question, and then try to answer the question based on relevant information as much as possible while ignoring irrelevant information.
            4. Output analysis results in the format of correctly parsed JSON without any additional descriptions that may disrupt JSON parsing, regardless of whether the user's question asks sample scripts or other formats. 
            5. The JSON output must contain the "scenario" property to briefly describe the function of this CLI script, a "commandSet" property containing the command info, arguments info, examples and descriptions of all the commands, and a "description" property to provide a more comprehensive description of the script but not too long.
            """
        ),
    },
    {
        "role": "user",
        "content": "How to Create an Azure Function that connects to an Azure Storage",
    },
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "scenario": "Create an Azure Function that connects to an Azure Storage",
                "commandSet": [
                    {
                        "command": "az functionapp create",
                        "arguments": [
                            "--name",
                            "--resource-group",
                            "--storage-account",
                            "--consumption-plan-location",
                            "--functions-version",
                        ],
                        "reason": "Create a serverless function app in the resource group",
                        "example": "az functionapp create --name $functionApp --resource-group $resourceGroup --storage-account $storage --consumption-plan-location $location --functions-version $functionsVersion",
                    },
                    {
                        "command": "az storage account show-connection-string",
                        "arguments": [
                            "--name",
                            "--resource-group",
                            "--query",
                            "--output",
                        ],
                        "reason": "Get the storage account connection string. (connstr will be used in subsequent commands)",
                        "example": "az storage account show-connection-string --name $storage --resource-group $resourceGroup --query connectionString --output tsv",
                    },
                    {
                        "command": "az functionapp config appsettings set",
                        "arguments": ["--name", "--resource-group", "--settings"],
                        "reason": "Update function app settings to connect to the storage account",
                        "example": "az functionapp config appsettings set --name $functionApp --resource-group $resourceGroup --settings StorageConStr=$connstr",
                    },
                ],
                "description": "Create an new Azure Function that connects to an Azure Storage by using connectionString",
            }
        ),
    },
]

_default_split_task = [
    {
        "role": "system",
        "content": textwrap.dedent(
            """\
            You are an assistant who breaks down user question into multiple corresponding step description and Azure CLI commands. You can complete the task based on the following steps:
            1. Determine whether the question can be completed by a set of Azure CLI commands. If not, please output empty array [] and end this task.
            2. Analyze the steps related to Azure CLI commands in this question and confirm each step must correspond to a single Azure CLI command.
            3. Output corresponding descriptions for each step without meaningless conjunctions. If a step can be completed by using an Azure CLI command that you know, output the corresponding command and parameters info of this step after the step description. Use "||" as a separator between step and command information.
            4. Ignore the step which contains general Azure CLI commands unrelated to specific scenarios in the question (such as 'az group create', 'az login').
            5. Ignore the step which contains non Azure CLI commands that do not start with "az" (such as docker, bash and kubectl commads).
            6. Ignore the step which contains the description unrelated to Azure CLI commands.
            7. If this question is too complex and requires many steps to be split, then only retain up to 8 of the most core steps.
            Finally, output the results as a JSON array."""
        ),
    },
    {
        "role": "user",
        "content": "How to create an Azure Function that connects to an Qumulo Storage?",
    },
    {
        "role": "assistant",
        "content": json.dumps(
            [
                "Create an Azure Function app||az functionapp create --name --resource-group --storage-account --consumption-plan-location --functions-version",
                "Create a Qumulo Storage account",
                "Show a connection string for storage account||az storage account show-connection-string --name --resource-group --query --output",
                "Add connection string to Azure Function settings||az functionapp config appsettings set --name --resource-group --settings",
            ]
        ),
    },
]

gs = json.dumps(_default_generate_scenario)
st = json.dumps(_default_split_task)

DEFAULT_GENERATE_SCENARIO_MSG = json.dumps(_default_generate_scenario)
DEFAULT_SPLIT_TASK_MSG = json.dumps(_default_split_task)
