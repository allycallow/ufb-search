from os import getenv

import boto3
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection

OPENSEARCH_DOMAIN_ENDPOINT = getenv("OPENSEARCH_DOMAIN_ENDPOINT")
IS_LOCAL = getenv("IS_LOCAL", "false").lower() == "true"
REGION = getenv("AWS_REGION", "eu-west-2")

if IS_LOCAL:
    client = OpenSearch(
        hosts=[{"host": OPENSEARCH_DOMAIN_ENDPOINT, "port": 9200}],
        http_auth=("admin", "39_e4a9lFg67"),
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False,
        connection_class=RequestsHttpConnection,
    )
else:
    session = boto3.Session()
    client = OpenSearch(
        hosts=[{"host": OPENSEARCH_DOMAIN_ENDPOINT, "port": 443}],
        http_auth=AWSV4SignerAuth(session.get_credentials(), REGION, "es"),
        connection_class=RequestsHttpConnection,
        use_ssl=True,
    )
