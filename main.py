import requests
import os
import guidance
import shutil
import tempfile
from dotenv import load_dotenv

load_dotenv()

api_url = "https://api.github.com/repos/{owner}/{repo}/releases"
owner = os.environ.get('OWNER')
repo = os.environ.get('REPO')
tag_file = os.environ.get('TAG_FILE')
release_notes_file = os.environ.get('RELEASE_NOTES_FILE')
openai_api_key = os.environ.get('OPENAI_API_KEY')

def get_release_info(tag):
    response = requests.get(api_url.format(
        owner=owner, repo=repo) + "/tags/" + tag)
    response.raise_for_status()
    return response.json()


def get_new_release_tags(saved_tag):
    page = 1
    new_tags = []
    found_saved_tag = False
    while True:
        response = requests.get(api_url.format(owner=owner, repo=repo), params={"page": page})
        response.raise_for_status()
        releases = response.json()
        if not releases:
            break
        for release in releases:
            tag = release["tag_name"]
            if tag == saved_tag:
                found_saved_tag = True
                break
            new_tags.append(tag)
        if found_saved_tag:
            break
        page += 1
    return new_tags[::-1]



def save_latest_release_tag(tag):
    with open(tag_file, "w") as f:
        f.write(tag)


def load_latest_release_tag():
    if os.path.exists(tag_file):
        with open(tag_file, "r") as f:
            return f.read()
    else:
        return None


def translate(text):
    guidance.llm = guidance.llms.OpenAI(
        model="gpt-3.5-turbo", api_key=openai_api_key)
    translate_text_in_jp = guidance('''{{#system~}}
  与えられたテキストを日本語に変換してください。
  {{~/system}}
  {{#user~}}
  {{user_input}}
  {{~/user}}
  {{#assistant~}}
  {{gen 'answer' temperature=1.0 max_tokens=2000}}
  {{~/assistant}}''')

    out = translate_text_in_jp(user_input=text)
    return out["answer"]

def write_release_notes(tag):
    release_info = get_release_info(tag)
    body = translate(release_info["body"])
    release_note = "# Release " + tag + "\n\n" + body + "\n\n"
    with tempfile.NamedTemporaryFile("w", delete=False) as temp:
        temp.write(release_note)
        if os.path.exists(release_notes_file):
            with open(release_notes_file, "r") as f:
                shutil.copyfileobj(f, temp)
    shutil.move(temp.name, release_notes_file)

def main():
    saved_tag = load_latest_release_tag()
    new_tags = get_new_release_tags(saved_tag)

    for tag in new_tags:
        print("New release: " + tag)
        write_release_notes(tag)

    if new_tags:
        save_latest_release_tag(new_tags[-1])


if __name__ == "__main__":
    main()
