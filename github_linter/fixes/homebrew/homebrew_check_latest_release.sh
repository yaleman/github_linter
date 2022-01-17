#!/bin/bash

# echo to stderr: https://stackpointer.io/script/shell-script-echo-to-stderr/355/


# get_latest_release from here https://gist.github.com/lukechilds/a83e1d7127b78fef38c2914c4ececc3c
get_latest_release() {
  curl --silent "$1" | grep -E '"(tag_name|name)\"' | head -n1 | sed -E 's/.*\"([^\"]+)\",/\1/'
}

SPECFILE=$(find "$(pwd)" -type f -name '*.rb' | head -n1)

if [ -z "${SPECFILE}" ]; then
    echo "Failed to find specfile, bailing!"
    exit 1
else
    echo "SPECFILE: ${SPECFILE}"
fi

# grab the update url from the spec file
URL=$(grep -E homepage "${SPECFILE}" | awk '{print $NF}' | tr -d '"')
if [ -z "${URL}" ]; then
    echo "Failed to find check URL, bailing!"
    exit 1
else
    echo "Check URL: ${URL}"
fi


# pull the latest version
LATEST=$(get_latest_release "${URL}" )
if [ -z "${LATEST}" ]; then
    echo "Failed to find latest version, bailing!"
    exit 1
else
    # echo "::set-env name=LATEST::${LATEST}"
    echo "Latest version ${LATEST}"
fi
CURRENT=$(grep -E 'version \"+' "${SPECFILE}" | awk '{print $NF}' | tr -d '"')

if [ "${CURRENT}" == "${LATEST}" ]; then
    echo "No change in version, quitting."
    exit 1
else
    echo "Version going from '${CURRENT}' to '${LATEST}'"
fi

# pull the download url from the spec file and update it
echo "Grabbing download URL"
DOWNLOAD_URL=$(grep -E 'url \"http.*' "${SPECFILE}" | awk '{print $NF}' | tr -d '"' | sed -E "s/#\{version\}/$LATEST/g")
if [ -z "${DOWNLOAD_URL}" ]; then
    echo "Failed to find download URL, bailing!"
    exit 1
else
    echo "Download URL: ${DOWNLOAD_URL}"
fi

echo "Grabbing filehash"
# calculate the shasum based on the file
FILEHASH=$(curl -L --silent "${DOWNLOAD_URL}" | shasum -a 256 | awk '{print $1}')
if [ -z "${FILEHASH}" ]; then
    echo "Couldn't get file hash, bailing"
    exit 1
else
    echo "Hash: ${FILEHASH}"
fi

echo "Updating file"
# updates the file
sed -i -E "s/version \\\".*/version \"${LATEST}\"/g" "${SPECFILE}"
sed -i -E "s/sha256 \\\".*/sha256 \"${FILEHASH}\"/g" "${SPECFILE}"

DIFF_LINES="$(git diff | wc -l)"
if [ "${DIFF_LINES}" -ne 0 ]; then
    echo "Changed, woo!"
else
    echo "No changes required."
fi
