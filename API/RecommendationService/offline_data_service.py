import asyncio
import os

from .cosmos_helper import query_recommendation_from_offline_data, query_recommendation_from_offline_data_2
from .util import get_latest_cmd, RecommendationSource, RecommendType, generated_cosmos_type, CosmosType


async def get_recommend_from_offline_data(command_list, recommend_type, error_info, top_num=50):
    loop = asyncio.get_event_loop()
    cosmos_type = generated_cosmos_type(recommend_type, error_info)
    commands = get_latest_cmd(command_list, 2)

    totalcount_threshold = int(os.environ["Solution_TotalCount_Threshold"]) if cosmos_type == CosmosType.Solution else int(os.environ["Command_TotalCount_Threshold"])
    ratio_threshold = int(os.environ["Solution_Ratio_Threshold"]) if cosmos_type == CosmosType.Solution else int(os.environ["Command_Ratio_Threshold"])

    if cosmos_type == CosmosType.Solution:
        return get_recommend_from_cosmos(commands[-1:], recommend_type, error_info, totalcount_threshold, ratio_threshold, top_num)
    else:
        # The recommended content matching the last two commands is preferred. If there is no data, it will fall back to the situation of matching the last command
        result_2_future = loop.run_in_executor(None, get_recommend_from_cosmos, commands[-2:], recommend_type, error_info, totalcount_threshold, ratio_threshold, top_num)
        result_future = loop.run_in_executor(None, get_recommend_from_cosmos, commands[-1:], recommend_type, error_info, totalcount_threshold, ratio_threshold, top_num)

        result_2 = await result_2_future
        if len(result_2) >= top_num:
            return result_2
        else:
            return result_2 + await result_future


def get_recommend_from_cosmos(commands, recommend_type, error_info, totalcount_threshold, ratio_threshold, top_num=50):
    if len(commands) == 2:
        query_items = list(query_recommendation_from_offline_data_2(commands[-2], commands[-1], recommend_type, error_info))
    else:
        query_items = list(query_recommendation_from_offline_data(commands[-1], recommend_type, error_info))

    result = []
    for item in query_items:
        if item['totalCount'] < totalcount_threshold:
            continue

        if item and 'nextCommand' in item:
            for command_info in item['nextCommand']:

                # The items in 'nextCommand' have been sorted according to frequency of occurrence
                command_info['ratio'] = float((int(command_info['count'])/int(item['totalCount'])))
                if command_info['ratio'] * 100 < ratio_threshold:
                    break

                if error_info:
                    command_info['type'] = RecommendType.Solution
                else:
                    command_info['type'] = RecommendType.Command
                    # Commands inputed by this user do not participate in recommendations for Command scenario
                    if command_info['command'] in commands:
                        continue

                command_info['usage_condition'] = get_usage_condition(command_info['ratio'])
                command_info['source'] = RecommendationSource.OfflineCaculation
                result.append(command_info)

    # Sort the calculated offline data according to the usage ratio and take the top n data
    if result:
        result = sorted(result, key=lambda x: x['ratio'], reverse=True)

    return result[0: top_num]


def get_usage_condition(ratio):
    if ratio >= 0.3:
        return 'Commonly used command by other users in next step'
    if ratio >= 0.5:
        return 'The most used command by other users in next step'
