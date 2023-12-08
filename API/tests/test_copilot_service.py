import asyncio
import json
import logging
import os
import threading
import typing
import unittest

import azure.functions as func
from azure.functions._abc import TraceContext, RetryContext
import msal

from common.validate import validate_command_set, initialize_validator


def generate_token():
    authority = os.environ["AUTHORITY"]
    client_id = os.environ["CLIENT_ID"]
    scope = [os.environ["SCOPE"]]
    secret = os.environ["SECRET"]
    app = msal.ConfidentialClientApplication(
        client_id, authority=authority,
        client_credential=secret
    )

    result = app.acquire_token_for_client(scopes=scope)
    return result['access_token']


class TestCopilotService(unittest.TestCase):
    QUESTIONS = [
        "How to Build out an end-to-end Azure Digital Twins solution that's driven by device data?",
        "I want to Create a custom VM image that you can use to deploy a virtual machine scale set.",
        "Could you help Use App Service authentication and authorization to secure my App Service apps?",
        "What is the CLI command to start the database instance of the Virtual Instance for SAP solution using Azure Center for SAP Solution?",
        "How to set up a new storage account and container in Azure?",
        "Can you guide me on how to create a new virtual network with a subnet in Azure?",
        "What are the steps to update the size of a virtual machine using Azure CLI?",
        "How do I delete a resource group along with all its resources in Azure?",
        "Can you show me how to enable diagnostics logs for an App Service?",
        "What is the process to connect an Azure SQL Database to Power BI using Azure Active Directory?",
        "How can I migrate my on-premises SQL Server database to Azure SQL Database?",
        "What is the procedure to create a new container registry in Azure?",
        "How do I list all the available VM images in a specific region using Azure CLI?",
        "Can you guide me on how to configure auto-shutdown for my VMs in Azure?",
        "How do I assign a static public IP address to a VM using Azure CLI?",
        "Can you guide me on how to configure virtual network peering between two virtual networks in different regions?",
        "How can I add a new disk to my existing VM using Azure CLI?",
        "What is the process to backup an Azure SQL Database using Azure CLI?",
        "How can I set up role-based access control (RBAC) for resources in my resource group?",
        "How do I restore my Azure SQL Database from a backup using Azure CLI?",
        "How to use the new Azure CLI feature to create a disk snapshot of a managed disk?",
        "What are the steps to enable Managed Service Identity (MSI) on an existing VM using Azure CLI?",
        "Can you guide me on how to set up Azure Private DNS zone using Azure CLI?",
        "How do I use Azure CLI to configure IP restrictions for an App Service?",
        "What is the process to create a new Azure Container Instance with a private IP address using Azure CLI?",
        "How can I set up custom RBAC roles for my resources?",
        "How do I use Azure CLI to create a virtual machine scale set with automatic OS image updates?",
        "Can you guide me on how to set up Azure Functions Premium Plan using Azure CLI?",
        "How do I use Azure CLI to attach an existing disk to a Virtual Machine Scale Set (VMSS)?",
        "What is the process to configure cross-region replication for my storage account blobs using Azure CLI?",
        "How do I set up a private endpoint for my Azure SQL Database?",
        "What are the steps to create a new Windows Virtual Desktop host pool using Azure CLI?",
        "How do I use Azure CLI to enable soft delete for blob data in my storage account?",
        "Can you guide me on how to set up an Application Gateway with custom probe settings using Azure CLI?",
        "What is the process to enable and configure network watcher traffic analytics using Azure CLI?",
    ]

    LATEST_USAGE_QUESTIONS = [
        'I\'m setting up an artifact streaming system in Azure. Could you guide me through the process of creating, displaying and updating an artifact streaming using Azure CLI in this context?',
        'Suppose I have started an artifact streaming operation for a project but due to some changes, I need to cancel it. Can you tell me the Azure CLI command for that?',
        'After initiating an artifact streaming operation, I want to monitor its progress. How can I do that using Azure CLI?',
        'When logging into my ACR, I want to validate if my registry name is correct to avoid any errors. How can I achieve this using Azure CLI?',
        'I am managing different projects under different resource groups in ACR. Now, I need to set credentials for one of them. Can you guide me on how to specify the resource group while setting ACR credentials using Azure CLI?',
        'I\'m trying to manage ACR cache within a specific project hosted under a particular resource group. How can I specify the resource group when managing ACR cache using Azure CLI?',
        'During the upgrade of my AKS nodepool, I want to slow down the upgrade process. Can you tell me how to set a drain timeout using Azure CLI?',
        'I am working with AppConfig snapshots and need to perform several operations including exporting a snapshot, making some changes, and then importing it back. Additionally, I want to verify my operations by listing all available snapshots. Could you guide me on how to achieve this using Azure CLI?',
        'As part of my project, I need to deploy a web app on windows container workers in a region where it is supported. Could you guide me on how to find such regions and then create and deploy my web app using Azure CLI?',
        'I am deploying my function app from a zip file and want to add deployer information for better telemetry. After deployment, I want to verify if the deployer information has been added correctly. Could you guide me on how to achieve this using Azure CLI?',
        'I am working on a project where I need to create a new Azure Stack group but I don\'t want to wait for the operation to complete. Could you guide me on how to create an Azure Stack group without waiting, and then check the status of this operation later using Azure CLI?',
        'I\'m working with Bicep files and I want to lint my Bicep file before deploying it. After linting, I want to deploy my Bicep file with supplemental parameters. Could you guide me on how to achieve this using Azure CLI?',
        'I am deploying a template with parameters whose definition uses a $ref. How can I determine the type of these parameters using Azure CLI during deployment?',
        'Could you guide me on how to create an ARO cluster with preconfigured NSGs enabled using Azure CLI?',
        'I am creating an Azure Red Hat OpenShift cluster and want to add network contributor to the NSG resource for the cluster Service Principal and First Party Service Principal. ',
        'I need to create a restore point for my virtual machine and want to encrypt the OS disk. Also, I want to verify the creation of the restore point afterward. ',
        'I am creating a restore point for my virtual machine and want to encrypt a data disk. After creating the restore point, I would like to list all available restore points.',
        'Could you guide me on how to create a disk optimized for frequent attachment and then attach it to my VM using Azure CLI?',
        'I am working with snapshots and need to create a snapshot through the ARM id of an elastic SAN volume snapshot.',
        'I am creating a new Managed HSM and want to assign a managed identity to it.',
        'I am starting a backup operation for my Key Vault and want to use a managed identity to exempt SAS token. After starting the backup operation, I want to check the status of this operation.',
        'I started a search job for my Log Analytics workspace table and now I want to cancel it. Could you guide me on how to cancel a search job using Azure CLI?',
        ' I am creating a new Log Analytics workspace and want to assign a user-assigned managed identity to it. Also, I want to list all Log Analytics workspaces in my resource group after creation.',
        'I am creating a new load balancer address pool and want to specify the synchronization mode.',
    ]

    # Copy from https://github.com/Azure/azure-functions-python-library/blob/0ca53b35491ce22569f012d485c9973050ea3227/tests/test_http_asgi.py#L128-L194
    @staticmethod
    def _generate_func_request(
            method="POST",
            url="https://function.azurewebsites.net/api/http?firstname=rt",
            headers=None,
            params=None,
            route_params=None,
            body=b'{ "lastname": "tsang" }'
    ) -> func.HttpRequest:
        if route_params is None:
            route_params = {}
        if headers is None:
            headers = {
                "Content-Type": "application/json",
                "x-ms-site-restricted-token": "xmsrt"
            }
        return func.HttpRequest(
            method=method,
            url=url,
            headers=headers,
            params=params,
            route_params=route_params,
            body=body
        )

    @staticmethod
    def _generate_func_context(
            invocation_id='123e4567-e89b-12d3-a456-426655440000',
            thread_local_storage=threading.local(),
            function_name='httptrigger',
            function_directory='/home/cli-copilot/wwwroot/httptrigger',
    ) -> func.Context:
        class MockTraceContext(TraceContext):
            def __init__(self):
                self.Traceparent = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"

            @property
            def trace_state(self) -> str:
                return "congo=t61rcWkgMzE"

            @property
            def trace_parent(self) -> str:
                return self.Traceparent

            @property
            def attributes(self) -> typing.Dict[str, str]:
                return {}

        class MockContext(func.Context):
            def __init__(self, ii, tls, fn, fd, tc, rc):
                self._invocation_id = ii
                self._thread_local_storage = tls
                self._function_name = fn
                self._function_directory = fd
                self._trace_context = tc
                self._retry_context = rc

            @property
            def invocation_id(self):
                return self._invocation_id

            @property
            def thread_local_storage(self):
                return self._thread_local_storage

            @property
            def function_name(self):
                return self._function_name

            @property
            def function_directory(self):
                return self._function_directory

            @property
            def trace_context(self):
                return self._trace_context

            @property
            def retry_context(self):
                return self._retry_context

        return MockContext(invocation_id, thread_local_storage, function_name,
                           function_directory, MockTraceContext(), RetryContext)

    @staticmethod
    def init_validator():
        asyncio.run(initialize_validator())

    @staticmethod
    def load_local_settings():
        if os.path.exists('../local.settings.json'):
            with open('../local.settings.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
                for k, v in settings['Values'].items():
                    os.environ[k] = v

    @staticmethod
    def copilot_from_gpt(question: str):
        TestCopilotService.load_local_settings()
        body = {
            "question": question,
            "history": [],
            "type": "GPTGeneration"
        }
        req = TestCopilotService._generate_func_request(url='http://localhost:9091/api/CopilotService',
                                                        body=json.dumps(body).encode('utf-8'))
        ctx = TestCopilotService._generate_func_context()

        try:
            from CopilotService import main
            resp: func.HttpResponse = main(req=req, context=ctx)
            data = resp.get_body().decode('utf-8')
            if resp.status_code != 200:
                return None, ctx, None, data
            scenarios = json.loads(data)['data']
            if len(scenarios) > 0:
                result = validate_command_set(scenarios[0]['commandSet'])
                return scenarios[0], ctx, result, None
            else:
                return None, ctx, None, None
        except Exception as e:
            logging.error(e)
            return None, ctx, None, e

    def test_sap_issue(self):
        self.init_validator()
        self.copilot_from_gpt('What is the CLI command to start the database instance of the Virtual Instance for SAP solution using Azure Center for SAP Solution?')

    def _test_questions(self, questions, file_name, epochs=3):
        if os.path.exists(file_name):
            with open(file_name, 'r', encoding='utf-8') as f:
                results = json.load(f)
        else:
            results = {}
        self.init_validator()
        for i in range(epochs):
            for question in questions:
                scenario, ctx, validate_result, exception = self.copilot_from_gpt(question)
                ctx = ctx.custom_context
                line = {
                    "duration": ctx.originalCall.duration,
                    "usage": ctx.originalCall.usage,
                    "sub": [{
                        "duration": call.duration,
                        "question": call.request,
                        "answer": call.response,
                        "usage": {
                            "model": call.usage.model,
                            "task": call.usage.gpt_task_name,
                            "estimate": {
                                "question": call.usage.estimated_question_tokens,
                                "history": call.usage.estimated_history_tokens,
                                "prompt": call.usage.estimated_prompt_tokens,
                                "total": call.usage.estimated_question_tokens + call.usage.estimated_history_tokens + call.usage.estimated_prompt_tokens,
                            },
                            "tokens": {
                                "prompt": call.usage.prompt_tokens,
                                "completion": call.usage.completion_tokens,
                                "total": call.usage.total_tokens,
                            }
                        } if call.usage else None
                    } for call in ctx.statistics.callGraph]
                }
                if not exception:
                    line["scenario"] = scenario
                    if validate_result:
                        line["errors"] = [str(r.result) for r in validate_result.errors]
                        line["example_errors"] = [str(r.example_result) for r in validate_result.example_errors]
                else:
                    line["exception"] = str(exception)
                if question not in results:
                    results[question] = []
                results[question].append(line)
                with open(file_name, 'w', encoding='utf-8', newline='') as f:
                    json.dump(results, f, indent=4)

    def test_batch_gpt_then_dump(self):
        self.init_validator()
        self._test_questions(self.QUESTIONS, 'test_batch_gpt_then_dump.json')

    def test_latest_usage(self):
        self.init_validator()
        self._test_questions(self.LATEST_USAGE_QUESTIONS, 'test_latest_usage.json')

    def test_kb(self):
        self.init_validator()
        with open('../../../eval-gpt/resources/scenarios/kb.txt', 'r', encoding='utf-8') as f:
            kb_scenarios = f.readlines()
        self._test_questions(['How to ' + s.strip('\n') for s in kb_scenarios], 'test_kb.json', 1)

    def test_gpt_gen01(self):
        self.init_validator()
        with open('../../../eval-gpt/resources/scenarios/gpt_gen01.txt', 'r', encoding='utf-8') as f:
            kb_scenarios = f.readlines()
        self._test_questions([s.strip('\n') for s in kb_scenarios if s], 'test_gpt_gen01.json', 1)

    def test_single_question(self):
        self.init_validator()
        self.copilot_from_gpt('How to Configure a GitHub Action that automates steps to build, push, and deploy a container image to Azure Container Instances')
