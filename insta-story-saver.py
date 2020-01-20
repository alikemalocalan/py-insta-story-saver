import datetime
import json
import os
import time
from urllib.parse import urlparse
from urllib.request import urlretrieve

from apscheduler.schedulers.blocking import BlockingScheduler
from instagram_private_api import Client

user_name = os.environ['USERNAME']
password = os.environ['PASSWORD']

result_path = os.environ['RESULT_PATH']

sched = BlockingScheduler()


class StorySaver:
    def __init__(self, user_name: str, password: str, result_file_path: str):
        self.user_name = user_name
        self.api = Client(user_name, password)
        self.api.login()
        self.rank_token = Client.generate_uuid()
        self.result_json = open(result_file_path, "a", encoding='utf-8')

    def getMyFollowingList(self) -> list:
        user_pk = self.api.user_detail_info(self.user_name)["user_detail"]["user"]["pk"]
        return self.api.user_following(user_pk, self.rank_token)["users"]

    def _saveStory(self, user_pk):
        stories = self.api.user_story_feed(user_pk).get("reel", "")
        if stories is not None:
            self.result_json.write(json.dumps(stories))
            self.result_json.write("\n")

            for item in stories.get("items", []):
                username = item["user"]["username"]

                img_url = item.get("image_versions2", []).get("candidates", [])[0]["url"]

                img_folder = result_path + "photos/" + username + "/"
                if not os.path.exists(img_folder):
                    os.makedirs(img_folder)

                img_filename = img_folder + urlparse(img_url).path.split("/")[-1]
                urlretrieve(img_url, img_filename)

                if item.get("video_versions", []):
                    video_url = item.get("video_versions", [])[0]["url"]
                    video_folder = result_path + "video/" + username + "/"
                    if not os.path.exists(video_folder):
                        os.makedirs(video_folder)
                    video_filename = video_folder + urlparse(video_url).path.split("/")[-1]
                    urlretrieve(video_url, video_filename)

                print(img_url)

    def downloadPictures(self):
        users = self.getMyFollowingList()
        for user in users:
            time.sleep(1)
            self._saveStory(str(user["pk"]))


story_saver = StorySaver(user_name, password, result_path + "stories.json")


@sched.scheduled_job('cron', hour=24)
def scheduleJob(self):
    print("Running at : " + str(datetime.datetime.now()))
    # self.downloadPictures()


sched.start()
