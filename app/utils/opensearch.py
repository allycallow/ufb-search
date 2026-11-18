from os import getenv

import boto3
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection

OPENSEARCH_DOMAIN_ENDPOINT = getenv("OPENSEARCH_DOMAIN_ENDPOINT")
IS_LOCAL = getenv("IS_LOCAL", "false").lower() == "true"
# False while ufb-iac's modules/opensearch stands in for the managed AWS
# domain pre-launch: a self-hosted container with no security plugin, so
# neither IAM request signing nor TLS certificate verification apply the
# way they do against the real domain (see ufb-iac's manage_opensearch).
OPENSEARCH_MANAGED = getenv("OPENSEARCH_MANAGED", "true").lower() == "true"
REGION = getenv("AWS_REGION", "eu-west-2")
# The backend gives a search 5 seconds, and top results makes two calls in a
# row, so each call must give up well before that.
OPENSEARCH_TIMEOUT_SECONDS = 2

if IS_LOCAL:
    client = OpenSearch(
        hosts=[{"host": OPENSEARCH_DOMAIN_ENDPOINT, "port": 9200}],
        http_auth=("admin", "39_e4a9lFg67"),
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False,
        connection_class=RequestsHttpConnection,
        timeout=OPENSEARCH_TIMEOUT_SECONDS,
    )
elif not OPENSEARCH_MANAGED:
    client = OpenSearch(
        hosts=[{"host": OPENSEARCH_DOMAIN_ENDPOINT, "port": 9200}],
        use_ssl=False,
        connection_class=RequestsHttpConnection,
        timeout=OPENSEARCH_TIMEOUT_SECONDS,
    )
else:
    session = boto3.Session()
    client = OpenSearch(
        hosts=[{"host": OPENSEARCH_DOMAIN_ENDPOINT, "port": 443}],
        http_auth=AWSV4SignerAuth(session.get_credentials(), REGION, "es"),
        connection_class=RequestsHttpConnection,
        timeout=OPENSEARCH_TIMEOUT_SECONDS,
        use_ssl=True,
    )
