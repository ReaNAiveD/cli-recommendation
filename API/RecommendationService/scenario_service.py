import os
from typing import List

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from .cosmos_helper import query_recommendation_from_e2e_scenario
from .util import (RecommendationSource, RecommendType, ScenarioSourceType,
                   get_latest_cmd)


def strip_az_in_command_set(command_set):
    """Remove `az ` in commands in command_set

    Args:
        command_set (list[dict]): list of commands

    Returns:
        list[dict]: list of filtered commands
    """
    result = []
    for command in command_set:
        if command["command"] and command["command"].startswith("az "):
            command["command"] = command["command"][3:]
            result.append(command)
    return result


def get_scenario_recommendation(command_list, top_num=50):
    source_type: List[ScenarioSourceType] = [ScenarioSourceType.SAMPLE_REPO]
    commands = get_latest_cmd(command_list)

    result = []
    for item in query_recommendation_from_e2e_scenario(commands[-1], source_type):
        if len(item['commandSet']) > 1:
            scenario = {
                'scenario': item['name'],
                'nextCommandSet': strip_az_in_command_set(item['commandSet'][1:]),
                'source': RecommendationSource.OfflineCaculation,
                'type': RecommendType.Scenario
            }
            if 'description' in item:
                scenario['reason'] = item['description']
            result.append(scenario)

    return result[0: top_num]


def get_search_results(trigger_commands: List[str], top: int = 5):
    """Search related sceanrios using cognitive search

    Args:
        trigger_commands (List[str]): list of commands used to search
        top (int, optional): top num of returned results. Defaults to 5.

    Returns:
        list[dict]: searched scenarios
    """
    if len(trigger_commands) == 0:
        return []
    service_endpoint = os.environ["SCENARIO_SEARCH_SERVICE_ENDPOINT"]
    search_client = SearchClient(endpoint=service_endpoint,
                                 index_name=os.environ["SCENARIO_SEARCH_INDEX"],
                                 credential=AzureKeyCredential(os.environ["SCENARIO_SEARCH_SERVICE_SEARCH_KEY"]))
    search_statement = ""
    if len(trigger_commands) > 1:
        search_statement = "(" + " OR ".join([f'"{cmd}"' for cmd in trigger_commands][:-1]) + ") AND "
    search_statement = search_statement + f'"{trigger_commands[-1]}"'
    search_statement = f'"{trigger_commands[-1]}" OR ({search_statement})'
    results = search_client.search(
        search_text=search_statement,
        include_total_count=True,
        search_fields=["commandSet/command"],
        highlight_fields="commandSet/command",
        top=top,
        query_type='full')
    results = list(results)
    return results


def get_scenario_recommendation_from_search(command_list, top_num=5):
    """Recommend Scenarios that current context could be in

    Args:
        command_list (list[str]): commands used to trigger
        top_num (int, optional): top num of recommended results. Defaults to 5.

    Returns:
        list[dict]: searched scenarios
    """
    if len(command_list) == 0:
        return []
    trigger_len = int(os.environ.get("ScenarioRecommendationTriggerLength", "3"))
    trigger_commands = get_latest_cmd(command_list, trigger_len)
    trigger_commands = [cmd[3:] if cmd.startswith("az ") else cmd for cmd in trigger_commands]
    searched = get_search_results(trigger_commands, top_num)

    results = []
    for item in searched:
        # get all commands in searched scenario with `az ` stripped
        cmds = [cmd['command'][3:] for cmd in item['commandSet'] if len(cmd['command']) > 3]
        # get indices of commands that the user has not executed yet, which need to be executed
        execute_index = [idx for idx, cmd in enumerate(cmds) if cmd not in trigger_commands]
        # avoid recommending scenarios to users which they have executed all commands
        if len(execute_index) == 0:
            continue
        scenario = {
            'scenario': item['name'],
            'nextCommandSet': strip_az_in_command_set(item['commandSet']),
            'source': RecommendationSource.Search,
            'type': RecommendType.Scenario,
            'executeIndex': execute_index,
            'score': item['@search.score']
        }
        if 'description' in item:
            scenario['reason'] = item['description']
        results.append(scenario)
    return results
