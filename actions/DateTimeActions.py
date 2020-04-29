import sys
import logging
        
from typing import Any, Text, Dict, List
#
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from time import localtime, strftime
##
# MATHS FUNCTIONS
##

class ActionTellTime(Action):
#
    def name(self) -> Text:
        return "action_tell_time"
#
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        slotsets = []
        dispatcher.utter_message(text="The time is {}".format(strftime("%I:%M %p", localtime())))
            
        return slotsets

class ActionTellDate(Action):
#
    def name(self) -> Text:
        return "action_tell_date"
#
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        slotsets = []
        dispatcher.utter_message(text="The date is {}".format(strftime("%d %B", localtime())))
            
        return slotsets
 
