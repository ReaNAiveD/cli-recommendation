import re
import json

from enum import Enum

class RecommendType(int, Enum):
    All = 1
    Solution = 2
    Command = 3
    Scenario = 4

class CosmosType(int, Enum):
    Command = 1
    Solution = 2
    Scenario = 3

class RecommendationSource(int, Enum):
    KnowledgeBase = 1
    OfflineCaculation = 2
    Aladdin = 3
    Search = 4


class ScenarioSourceType(int, Enum):
    SAMPLE_REPO = 1
    DOC_CRAWLER = 2
    MANUAL_INPUT = 3


def get_cosmos_type(recommend_type):
    if not recommend_type:
        return

    Recommend_to_cosmos = {
        RecommendType.Command : CosmosType.Command,
        RecommendType.Solution : CosmosType.Solution,
        RecommendType.Scenario : CosmosType.Scenario
    }
    try:
        return Recommend_to_cosmos[recommend_type]
    except KeyError:
        return None


def generated_cosmos_type(recommend_type, has_error):
    cosmos_type = get_cosmos_type(recommend_type)
    if cosmos_type:
        return cosmos_type

    if recommend_type == RecommendType.All:
        if has_error:
            return CosmosType.Solution
        else:
            return str(CosmosType.Scenario.value) + "," + str(CosmosType.Command.value)


def need_error_info(recommend_type):
    if recommend_type in [ RecommendType.All, RecommendType.Solution]:
        return True
    return False


def need_aladdin_recommendation(recommend_type, error_info):
    if recommend_type == RecommendType.Command:
        return True
    if recommend_type == RecommendType.All and not error_info:
        return True
    return False


def need_offline_recommendation(recommend_type, error_info):
    if recommend_type == RecommendType.Command:
        return True
    if recommend_type == RecommendType.All and not error_info:
        return True
    return False


def need_scenario_recommendation(recommend_type, error_info):
    if recommend_type == RecommendType.Scenario:
        return True
    if recommend_type == RecommendType.All and not error_info:
        return True
    return False


def parse_error_info(error_info):
    ''' Ignore the value and put the other parts into the array '''
    if not error_info:
        return []

    error_info = error_info.split('.')[0]
    split_str = "|*Split*|"
    error_info = re.sub(" \_([^ ]*?)\_ ", split_str, error_info)
    return error_info.split(split_str)


def get_latest_cmd(command_list, num=1):
    command_list_data = json.loads(command_list)
    # If there is no command has been executed before, assume that the user's first command is "group create"
    if len(command_list_data) == 0:
        return "group create"

    commands = []
    for command_item in command_list_data:
        cmd = json.loads(command_item)
        commands.append(cmd['command'])

    return commands[-num:]


def generated_query_kql(command, recommend_type, error_info):
    query = "SELECT * FROM c WHERE c.command = '{}' ".format(command)

    cosmos_type =  generated_cosmos_type(recommend_type, error_info)
    if isinstance(cosmos_type, str):
        query += " and c.type in ({}) ".format(cosmos_type)
    elif isinstance(cosmos_type, int):
        query += " and c.type = {} ".format(cosmos_type)

    # If there is an error message, recommend the solution first
    if error_info and need_error_info(recommend_type):
        error_info_arr = parse_error_info(error_info)
        for info in error_info_arr:
            query += " and CONTAINS(c.errorInformation, '{}', true) ".format(info)

    return query
