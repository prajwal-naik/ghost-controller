import requests
import os
import logging

logging.basicConfig(level=logging.INFO)

def getOrCreateISO(url: str, version: str, architecture: str) -> str:

    downloadUrl = "https://{url}/alpine/v{versionPrefix}/releases/{architecture}/alpine-standard-{version}-{architecture}.iso" \
        .format(url=url, versionPrefix=".".join(version.split(".")[:2]), version = version, architecture=architecture)

    response = requests.get(downloadUrl)
    
    file_path = os.path.join(os.getcwd(), "utils", "alpine-standard-{version}-{architecture}.iso".
                            format(version=version, architecture=architecture))
    
    if(os.path.exists(file_path)):
        logging.info("ISO file exists: {path}".format(path = file_path))
        return file_path
    else:
        if response.status_code == 200:
            with open(file_path, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            logging.info("Downloaded Alpine Linux ISO at ---> {path}".format(path = file_path))
            return file_path
        else:
            raise Exception("Failed to download ISO from {downloadUrl}".format(downloadUrl = downloadUrl))
    
if __name__ == "__main__":
    getOrCreateISO("dl-cdn.alpinelinux.org", "3.20.0", "aarch64")
    
