from typing import List, Optional
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

import os


def get_search_results(search_statement: str, top: int = 5, search_fields: Optional[List[str]] = None):
    service_endpoint = os.environ["SCENARIO_SEARCH_SERVICE_ENDPOINT"]
    search_client = SearchClient(endpoint=service_endpoint,
                                 index_name=os.environ["SCENARIO_SEARCH_INDEX"],
                                 credential=AzureKeyCredential(os.environ["SCENARIO_SEARCH_SERVICE_SEARCH_KEY"]))

    results = search_client.search(
        search_text=search_statement,
        include_total_count=True,
        search_fields=search_fields,
        highlight_fields=", ".join(search_fields) if search_fields else None,
        top=top,
        query_type='full')
    results = list(results)
    for result in results:
        result.pop("rid")
        result["score"] = result.pop("@search.score")
        result["highlights"] = result.pop("@search.highlights")
        result["scenario"] = result.pop("name")
        if result["highlights"] and "name" in result["highlights"].keys():
            result["highlights"]["scenario"] = result["highlights"].pop("name")
    return results
