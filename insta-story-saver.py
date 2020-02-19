import datetime
import json
import logging
import os
import time
from urllib.parse import urlparse
from urllib.request import urlretrieve

import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from instagram_private_api import Client

logging.basicConfig(level=logging.DEBUG)
logging.debug("Script triggered at : " + str(datetime.datetime.now()))

user_name = os.environ['USERNAME']
password = os.environ['PASSWORD']

sched = BlockingScheduler()


class StorySaver:
    def __init__(self, user_name: str, password: str, result_file_path: str):
        self.user_name = user_name
        self.api = Client(user_name, password)
        self.api.login()
        self.rank_token = Client.generate_uuid()
        # self.result_json = open(result_file_path, "w", encoding='utf-8')

    def getMyFollowingList(self) -> list:
        user_pk = self.api.user_detail_info(self.user_name)["user_detail"]["user"]["pk"]
        return self.api.user_following(user_pk, self.rank_token)["users"]

    def _saveStory(self, user_pk):
        stories = self.api.user_story_feed(user_pk).get("reel", "")
        if stories is not None:
            # self.result_json.write(json.dumps(stories))
            # self.result_json.write("\n")

            for item in stories.get("items", []):
                username = item["user"]["username"]

                img_url = item.get("image_versions2", []).get("candidates", [])[0]["url"]
                img_folder = "photos/" + username + "/"
                img_filename = img_folder + urlparse(img_url).path.split("/")[-1]
                self.save_To_S3(img_filename, img_url)

                if item.get("video_versions", []):
                    video_url = item.get("video_versions", [])[0]["url"]
                    video_folder = "video/" + username + "/"
                    video_filename = video_folder + urlparse(video_url).path.split("/")[-1]
                    self.save_To_S3(video_filename, video_url)
                logging.debug(img_url)

    def startSave(self):
        users = self.getMyFollowingList()
        for user in users:
            time.sleep(1)
            self._saveStory(str(user["pk"]))

    @staticmethod
    def saveFileSystem(url, path_and_filename):
        if not os.path.exists(path_and_filename):
            os.makedirs(path_and_filename)
        urlretrieve(url, path_and_filename)

    @staticmethod
    def save_To_S3(s3_folder, url):
        service_url = "https://url-2-s3.herokuapp.com/upload"

        payload = json.dumps({"url": url, "fileNameAndPath": s3_folder})
        headers = {'Content-Type': 'application/json'}
        response = requests.request("POST", service_url, headers=headers, data=payload)
        print(response.text.encode('utf8'))


story_saver = StorySaver(user_name, password,
                         f"stories-{datetime.datetime.now().strftime('%Y-%m-%d-%H')}.json")


@sched.scheduled_job('cron', hour=23)
def scheduleJob():
    logging.debug("Running at : " + str(datetime.datetime.now()))
    story_saver.startSave()


sched.start()
