import os, json, hashlib, requests, boto3
from pathlib import Path

data = json.loads(Path("posts.json").read_text())
post = next(p for p in data if p.get("video", {}).get("url"))
url = post["video"]["url"]
response = requests.get(url, timeout=60)
response.raise_for_status()
body = response.content
digest = hashlib.sha256(body).hexdigest()
s3 = boto3.client("s3", endpoint_url="https://" + os.environ["R2_ACCOUNT_ID"] + ".r2.cloudflarestorage.com", region_name="auto")
key = "hidjaz/instagram/videos/" + post["code"] + ".mp4"
s3.put_object(Bucket=os.environ["R2_BUCKET_NAME"], Key=key, Body=body, Metadata={"sha256": digest})
head = s3.head_object(Bucket=os.environ["R2_BUCKET_NAME"], Key=key)
assert head["ContentLength"] == len(body)
assert head["Metadata"]["sha256"] == digest
print("Verified:", key, digest)
