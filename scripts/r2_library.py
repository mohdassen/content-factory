#!/usr/bin/env python3
import argparse
import mimetypes
import os
from pathlib import Path

import boto3


def client():
    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def upload(local_path: str, key: str | None = None):
    bucket = os.environ.get("R2_BUCKET", "content-factory-images")
    p = Path(local_path)
    key = key or p.name
    ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    client().upload_file(str(p), bucket, key, ExtraArgs={"ContentType": ctype})
    print(f"uploaded r2://{bucket}/{key}")


def list_objects(prefix: str = ""):
    bucket = os.environ.get("R2_BUCKET", "content-factory-images")
    paginator = client().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            print(obj["Key"])


def main():
    p = argparse.ArgumentParser(description="Content Factory Cloudflare R2 image library")
    sub = p.add_subparsers(dest="cmd", required=True)
    up = sub.add_parser("upload")
    up.add_argument("path")
    up.add_argument("--key")
    ls = sub.add_parser("list")
    ls.add_argument("--prefix", default="")
    args = p.parse_args()
    if args.cmd == "upload":
        upload(args.path, args.key)
    else:
        list_objects(args.prefix)


if __name__ == "__main__":
    main()
