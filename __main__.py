print("Loading libraries")
import asyncio
import os
import time

import aiohttp
import jwt
from gidgethub.aiohttp import GitHubAPI


def get_jwt(app_id):

    # TODO: read is as an environment variable
    path_to_private_key = os.getenv("PEM_FILE_PATH")
    pem_file = open(path_to_private_key, "rt").read()

    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + (10 * 60),
        "iss": app_id,
    }
    encoded = jwt.encode(payload, pem_file, algorithm="RS256")
    bearer_token = encoded.decode("utf-8")

    return bearer_token


async def get_installation(gh, jwt, username):
    async for installation in gh.getiter(
        "/app/installations",
        jwt=jwt,
        accept="application/vnd.github.machine-man-preview+json",
    ):
        if installation["account"]["login"] == username:
            return installation

    raise ValueError(f"Can't find installation by that user: {username}")


async def get_installation_access_token(gh, jwt, installation_id):
    # doc: https: // developer.github.com/v3/apps/#create-a-new-installation-token

    access_token_url = (
        f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    )
    response = await gh.post(
        access_token_url,
        data=b"",
        jwt=jwt,
        accept="application/vnd.github.machine-man-preview+json",
    )
    # example response
    # {
    #   "token": "v1.1f699f1069f60xxx",
    #   "expires_at": "2016-07-11T22:14:10Z"
    # }

    return response


async def main():
    print("Determining version")
    os.system("git describe --tags --dirty > version")
    version = open("version").read().strip()
    print("Version:", version)
    print("Authenticating")
    async with aiohttp.ClientSession() as session:
        app_id = os.getenv("GH_APP_ID")

        jwt = get_jwt(app_id)
        gh = GitHubAPI(session, "certik")

        try:
            installation = await get_installation(gh, jwt, "certik")

        except ValueError as ve:
            # Raised if Mariatta did not installed the GitHub App
            print(ve)
        else:
            access_token = await get_installation_access_token(
                gh, jwt=jwt, installation_id=installation["id"]
            )

            # treat access_token as if a personal access token

            print("Token obtained")
            from github3 import login
            gh = login("TruchasUploader", access_token["token"])
            repo = gh.repository("certik", "gh_app_demo")

            print("Creating a release")
            r = repo.create_release(version,
                    name="Release version %s" % version,
                    body="",
                    draft=False)
            print("Uploading a.txt")
            f = open("a.txt")
            s = r.upload_asset("text/plain", "a.txt", f)
            print("Uploaded:")
            print(s.browser_download_url)
            print("Uploading bzip")
            f = open("truchas-3.1.0.tar.bz2", "rb")
            s = r.upload_asset("application/x-bzip2", "truchas-3.1.0.tar.bz2", f)
            print("Uploaded:")
            print(s.browser_download_url)



asyncio.run(main())
