import boto3
import json
import copy
from botocore.config import Config

from langchain_aws import BedrockEmbeddings
from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine
from src.opensearch import OpenSearchHybridRetriever, OpenSearchClient

    
def converse_with_bedrock(sys_prompt, usr_prompt):
    temperature = 0.0
    top_p = 0.1
    top_k = 1
    inference_config = {"temperature": temperature, "topP": top_p}
    additional_model_fields = {"top_k": top_k}
    response = boto3_client.converse(
        modelId=llm_model, 
        messages=usr_prompt, 
        system=sys_prompt,
        inferenceConfig=inference_config,
        # additionalModelRequestFields=additional_model_fields
    )
    return response['output']['message']['content'][0]['text']

def init_boto3_client(region: str):
    retry_config = Config(
        region_name=region,
        retries={"max_attempts": 10, "mode": "standard"}
    )
    return boto3.client("bedrock-runtime", region_name=region, config=retry_config)

def init_search_resources(region_name):  
    embedding_model = BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0", region_name=region_name, model_kwargs={"dimensions":1024})
    sql_search_client = OpenSearchClient(emb=embedding_model, index_name='example_queries', mapping_name='mappings-sql', vector="input_v", text="input", output=["input", "query"])
    table_search_client = OpenSearchClient(emb=embedding_model, index_name='schema_descriptions', mapping_name='mappings-detailed-schema', vector="table_summary_v", text="table_summary", output=["table_name", "table_summary"])

    sql_retriever = OpenSearchHybridRetriever(sql_search_client, k=10)
    table_retriever = OpenSearchHybridRetriever(table_search_client, k=10)
    return sql_search_client, table_search_client, sql_retriever, table_retriever

def get_column_description(table_name):
    query = {
        "query": {
            "match": {
                "table_name": table_name
            }
        }
    }
    response = table_search_client.conn.search(index=table_search_client.index_name, body=query)

    if response['hits']['total']['value'] > 0:
        source = response['hits']['hits'][0]['_source']
        columns = source.get('columns', [])
        if columns:
            return {col['col_name']: col['col_desc'] for col in columns}
        else:
            return {}
    else:
        return {}


def create_prompt(sys_template, user_template, **kwargs):
    sys_prompt = [{"text": sys_template.format(**kwargs)}]
    usr_prompt = [{"role": "user", "content": [{"text": user_template.format(**kwargs)}]}]
    return sys_prompt, usr_prompt


def search_by_keywords(keyword):
    query = {
        "size": 10, 
        "query": {
            "nested": {
                "path": "columns",
                "query": {
                    "match": {
                        "columns.col_desc": f"{keyword}"
                    }
                },
                "inner_hits": {
                    "size": 1, 
                    "_source": ["columns.col_name", "columns.col_desc"]
                }
            }
        },
        "_source": ["table_name"]
    }
    response = table_search_client.conn.search(
        index=table_search_client.index_name,
        body=query
    )
    
    search_result = ""
    try:
        results = []
        table_names = set()  
        if 'hits' in response and 'hits' in response['hits']:
            for hit in response['hits']['hits']:
                table_name = hit['_source']['table_name']
                table_names.add(table_name)  
                for inner_hit in hit['inner_hits']['columns']['hits']['hits']:
                    column_name = inner_hit['_source']['col_name']
                    column_description = inner_hit['_source']['col_desc']
                    results.append({
                        "table_name": table_name,
                        "column_name": column_name,
                        "column_description": column_description
                    })
                    if len(results) >= 5:
                        break
                if len(results) >= 5:
                    break
        search_result += json.dumps(results, ensure_ascii=False)
    except:
        search_result += f"{keyword} not found"
    return search_result     


session = boto3.session.Session()
region_name = session.region_name

boto3_client = init_boto3_client(region_name)
llm_model = "us.amazon.nova-pro-v1:0"
sql_search_client, table_search_client, sql_retriever, table_retriever = init_search_resources(region_name)


######################################################       
# Grape Node 정의
######################################################       
from textwrap import dedent

csv_list_response_format = "Your response should be a list of comma separated values, eg: `foo, bar, baz` or `foo,bar,baz`"
json_response_format = dedent("""
    The output should be formatted as a JSON instance that conforms to the JSON schema below.

    As an example, for the schema {"properties": {"foo": {"title": "Foo", "description": "a list of strings", "type": "array", "items": {"type": "string"}}}, "required": ["foo"]}
    the object {"foo": ["bar", "baz"]} is a well-formatted instance of the schema. 
    The object {"properties": {"foo": ["bar", "baz"]}} is not well-formatted.

    Here is the output schema:
    ```
    {
        "properties": {
            "setup": {
                "title": "Setup", 
                "description": "question to set up a joke", 
                "type": "string"
            }, 
            "punchline": {
                "title": "Punchline", 
                "description": "answer to resolve the joke", 
                "type": "string"
            }
        }, 
        "required": ["setup", "punchline"]
    }
    ```
""")


class NodeTester:
    '''
    test_state = {
     "question": "서울시의 인구 통계를 보여줘",
     "intent": "",
     "sample_queries": [],
     "readiness": "",
     "tables_summaries": [],
     "table_names": ["population", "demographics"],
     "table_details": [],
     "query_state": {},
     "next_action": "",
     "answer": "",
     "dialect": "postgresql"
    }
    '''
    def __init__(self):
        pass

    def test(self, node_function, test_state):
        result = node_function(test_state)
        print("## Test Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        return result


