# -*- coding: utf-8 -*-
import tweepy

class TwitterInterface:
    def __init__(self, options):
        self.auth = tweepy.OAuthHandler(options["twitter_cons_key"],
                                    options["twitter_cons_secret"])
        self.auth.set_access_token(options["twitter_access_token"],
                                    options["twitter_access_secret"])
        self.api = tweepy.API(self.auth)
        self.options = options

     # creates telemetry text
    def gen_telemetry_text(self, telem):
        # convert coordinates (+/-)
        if telem["lat"][len(telem["lat"])-1] == 'S':
            telem["lat"] = "-" + telem["lat"][0:len(telem["lat"])-1].lstrip("0")
        else:
            telem["lat"] = telem["lat"][0:len(telem["lat"])-1].lstrip("0")

        if telem["lon"][len(telem["lon"])-1] == 'W':
            telem["lon"] = "-" + telem["lon"][0:len(telem["lon"])-1].lstrip("0")
        else:
            telem["lon"] = telem["lon"][0:len(telem["lon"])-1].lstrip("0")

        # ok, create tweet text
        text = "EKI-1 🎈"
        text += "está a "
        text += str(telem["alt"]) + "m de altura, "
        text += "presión de " + str(telem["baro"]) + " mBar, "
        text += "y a " + str(telem["tout"]) + "ºC, sobrevolando: / "
        text += "EKI-1 🎈"
        text += str(telem["alt"]) + " m-ko altitudean, "
        text += str(telem["baro"]) + " mBar-eko presioa, "
        text += "eta " + str(telem["tout"]) + "ºC-tan dago, honen gainean: "
        text += "http://www.openstreetmap.org/?mlat="
        text += str(telem["lat"]) + "&mlon="
        text += str(telem["lon"]) + "&zoom=14"

        return text

    # sends a tweet with the telemetry
    def tweet_telemetry(self, telem):
        # check telemetry (dict 13 elements)
        if len(telem) < 12:
            return "Error, not enough fields"

        # generate status message
        status_text = self.gen_telemetry_text(telem)

        # insert tweet
        try:
            if self.options["twitter_thread"] != 0:
                self.api.update_status(status=status_text, in_reply_to_status_id=self.options["twitter_thread"])
                return "Ok"
            else:
                self.api.update_status(status=status_text)
                return "Ok"
        except Exception as e:
                return "Error enviando tweet: " + str(e)

    # Uploads an image to twitter
    def tweet_image(self, image_path):
        # upload the image (Commented the modern API for python3)
        #media_id = None
        #try:
        #    media_id = api.media_upload(filename=image_path)
        #except tweepy.TweepError as e:
        #    return "Error subiendo la imagen"

        # ok, create tweet text
        status_text = "Esta es la última imagen recibida por EKI-1: 🎈 / "
        status_text += "Hau da EKI-1ek jasotako azken argazkia: 🎈 "

        # send tweet
        try:
            if self.options["twitter_thread"] != 0:
                #self.api.update_status(status=status_text,
                #        in_reply_to_status_id=self.options["twitter_thread"],
                #        media_ids=[media_id.media_id_string])
                self.api.update_with_media(status=status_text,
                        in_reply_to_status_id=self.options["twitter_thread"],
                        filename=image_path)
                return "Ok"
            else:
                #self.api.update_status(status=status_text,
                #        media_ids=[media_id.media_id_string])
                self.api.update_with_media(status=status_text,
                        filename=image_path)
                return "Ok"
        except Exception as e:
            return "Error tweeting image: " + str(e)

