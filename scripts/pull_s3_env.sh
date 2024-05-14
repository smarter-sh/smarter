
#!/bin/bash

bucket=$1
local_dir="/smarter"
folder="settings"

if aws s3 ls "s3://$bucket" 2>&1 | grep -q 'NoSuchBucket'
then
    echo "Copying AWS S3 bucket folder..."
    aws s3 cp "s3://$bucket/$folder" "$local_dir" --recursive
else
    echo "Syncing AWS S3 bucket folder..."
    aws s3 sync "s3://$bucket/$folder" "$local_dir"
fi
