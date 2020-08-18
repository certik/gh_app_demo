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

            # Example, creating a GitHub issue as a GitHub App
            gh_app = GitHubAPI(session, "TruchasUploader", oauth_token=access_token["token"])
            s = await gh_app.post(
                "/repos/certik/gh_app_demo/issues",
                data={
                    "title": "We got a problem 🤖",
                    "body": "Use more emoji! (I'm a GitHub App!) ",
                },
            )
            print("issue created")

            # https://docs.github.com/en/rest/reference/repos#create-a-release
            s = await gh_app.post(
                "/repos/certik/gh_app_demo/releases",
                data={
                    "tag_name": "v0.1.6",
                    "name": "my release",
                    "body": "Use more emoji! (I'm a GitHub App! 🤖)",
                    "draft": False,
                },
            )
            print("release created")

            # https://docs.github.com/en/rest/reference/repos#upload-a-release-asset
            assets_url = s["upload_url"]
            fdata = open("a.txt").read()
            s = await gh_app.post(
                assets_url,
                url_vars={
                    "content-length": len(fdata),
                    "content-type": "text/plain",
                    "name": "a.txt",
                },
                data=fdata
            )
            print("asset uploaded")



asyncio.run(main())
