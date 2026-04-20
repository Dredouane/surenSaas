#!/bin/bash
# Test curl pour upload de dossier AO

curl -X POST http://localhost:3000/api/v1/ao/upload-folder \
  -H "Cookie: session_token=$1" \
  -F "folder_zip=@/home/redouane/dev/AI-ERA/dce-v2.zip" \
  -v
