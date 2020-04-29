import sys
import logging
import json
import os
import yaml
from socket import error as socket_error        
from typing import Any, Text, Dict, List
#
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from mediawiki import MediaWiki
from wikidata.client import Client
import requests        
import wptools        
import paho.mqtt.client as mqtt

# config from main source. will need to be updated if action server is hosted elsewhere        
F = open(os.path.join(os.path.dirname(__file__), '../src/config-all.yaml'), "r")
CONFIG = yaml.load(F.read(), Loader=yaml.FullLoader)

def publish(topic,payload):        
    client = mqtt.Client()
    client.username_pw_set(CONFIG.get('mqtt_user'), CONFIG.get('mqtt_password'))
    client.connect(CONFIG.get('mqtt_hostname'), CONFIG.get('mqtt_port'), 60)
    # client.username_pw_set('hermod_server','hermod')
    # client.connect("localhost", 1883, 60)
    client.publish(topic,json.dumps(payload))

##
# WIKIPEDIA FUNCTIONS
##

# text search wikipedia link  
# https://en.wikipedia.org/w/index.php?search=Grey+Geese&title=Special%3ASearch&fulltext=1&ns0=1



class ActionSearchWiktionary(Action):
#
    def name(self) -> Text:
        return "action_search_wiktionary"
#
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        logger = logging.getLogger(__name__)    
        logger.debug('DEFINE ACTION')
        #logger.debug(CONFIG)
        logger.debug(tracker.current_state())
        last_entities = tracker.current_state()['latest_message']['entities']
        site = tracker.current_state().get('sender_id')
        word = ''
        for raw_entity in last_entities:
            logger.debug(raw_entity)
            if raw_entity.get('entity','') == "word":
                word = raw_entity.get('value','')
        
        if len(word) > 0:
            #dispatcher.utter_message(text=)
            publish('hermod/'+site+'/tts/say',{"text":"Looking now"})
            publish('hermod/'+site+'/display/startwaiting',{})

            result = self.lookup(word)
            if result and len(result.get('definition','')) > 0:
                publish('hermod/'+site+'/display/show',{'buttons':[{"label":'date',"text":'what is the date'},{"label":'time',"nlu":'ask_time'},{"label":'link',"frame":'https://en.wiktionary.org/wiki/'+word}]})
                publish('hermod/'+site+'/display/show',{'frame':'https://en.wiktionary.org/wiki/'+word})
                dispatcher.utter_message(text="The meaning of "+word+" is "+ result.get('definition',''))
                # TODO send hermod/XX/display/url   
            else:
                dispatcher.utter_message(text="I can't find the word "+word)
            publish('hermod/'+site+'/display/stopwaiting',{})
        else:
            dispatcher.utter_message(text="I didn't hear the word you want defined. Try again")
       
        slotsets = []
        return slotsets
        
        
    def lookup(self,word):
        wikipedia = MediaWiki()
        wikipedia.set_api_url('https://en.wiktionary.org/w/api.php')
        matches = {}
        search_results = wikipedia.opensearch(word)
        if len(search_results) > 0:
            page_title = search_results[0][0]
            page = wikipedia.page(page_title)
            parts = page.content.split("\n")
            i = 0
            while i < len(parts):
                definition = ""
                part = parts[i].strip()
                
                if part.startswith("=== Verb ===") or part.startswith("=== Noun ===") or part.startswith("=== Adjective ==="):
                    #print(part)
                    # try to skip the first two lines after the marker
                    if (i + 1) < len(parts): 
                        definition  = parts[i+1]
                    if (i + 2) < len(parts) and len(parts[i+2].strip()) > 0: 
                        definition  = parts[i+2]
                    if (i + 3) < len(parts) and len(parts[i+3].strip()) > 0: 
                        definition  = parts[i+3]
                
                
                if part.startswith("=== Adjective ===") and not 'adjective' in matches:
                    matches['adjective'] = definition
                if part.startswith("=== Noun ===") and not 'noun' in matches:
                    matches['noun'] = definition
                if part.startswith("=== Verb ===") and not 'verb' in matches:
                    matches['verb'] = definition
                    
                i = i + 1
            final = ""
            
            # prefer verb, noun then adjective
            if matches.get('adjective',False):
                final = matches.get('adjective')
            if matches.get('noun',False):
                final = matches.get('noun')
            if matches.get('verb',False):
                final = matches.get('verb')
            # strip leading bracket comment
            if final[0] == '(':
                close = final.index(")") + 1
                final = final[close:]
            matches['definition'] = final
        return matches
        
        
#
class ActionSearchWikipedia(Action):

    def name(self) -> Text:
        return "action_search_wikipedia"
#
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        logger = logging.getLogger(__name__)    
        logger.debug('DEFINE ACTION')
        logger.debug(tracker.current_state())
        last_entities = tracker.current_state()['latest_message']['entities']
        word = ''
        for raw_entity in last_entities:
            logger.debug(raw_entity)
            if raw_entity.get('entity','') == "thing":
                word = raw_entity.get('value','')
            if raw_entity.get('entity','') == "place":
                word = raw_entity.get('value','')
            if raw_entity.get('entity','') == "person":
                word = raw_entity.get('value','')
        site = tracker.current_state().get('sender_id')        
        if len(word) > 0:
            publish('hermod/'+site+'/tts/say',{"text":"Looking now"})
            publish('hermod/'+site+'/display/startwaiting',{})
            result = self.lookup(word)
            if result and len(result) > 0:
                dispatcher.utter_message(text=word + ". " + result)
                # TODO send hermod/XX/display/url  {'url':'https://en.wiktionary.org/wiki/'+word} 
            else:
                dispatcher.utter_message(text="I can't find the topic "+word)
        else:
            dispatcher.utter_message(text="I didn't hear your question. Try again")
        publish('hermod/'+site+'/display/stopwaiting',{})
       
        slotsets = []
        return slotsets
        
    def lookup(self,word):
        wikipedia = MediaWiki()
        #wikipedia.set_api_url('https://en.wikpedia.org/w/api.php')
        summary = ''
        search_results = wikipedia.opensearch(word)
        if len(search_results) > 0:
            page_title = search_results[0][0]
            page = wikipedia.page(page_title)
            parts = page.summary.split('. ')
            summary = parts[0];
        return summary
        
class ActionSearchWikipediaPerson(ActionSearchWikipedia):
    def name(self) -> Text:
        return "action_search_wikipedia_person"
    
class ActionSearchWikipediaPlace(ActionSearchWikipedia):
    def name(self) -> Text:
        return "action_search_wikipedia_place"



class ActionSearchWikidata(Action):
    
    wikidata_attributes = {
        "person": {
            "P31":"instance of",
            #person
            "P106":"occupation",
            "P27":"country of citizenship",
            "P19":"place of birth",
            "P1569":"date of birth",
            "P570":"place of death",
            "P26":"spouse",
            "P140":"religion",
            "P21":"sex or gender",
            "P106":"occupation"
        },
        "place": {
            "P31":"instance of",
            # place
            "P36":"capital",
            "P1451":"motto text",
            "P474":"country calling code",
            "P1082":"population",
            "P38":"currency",
            "P1906":"office held by head of state",
            "P37":"official language",
            "P30":"continent"
        }
    }
#
    def name(self) -> Text:
        return "action_search_wikidata"
#
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        logger = logging.getLogger(__name__)    
        logger.debug('DEFINE ACTION')
        logger.debug(tracker.current_state())
        last_entities = tracker.current_state()['latest_message']['entities']
        attribute = ''
        thing = ''
        for raw_entity in last_entities:
            logger.debug(raw_entity)
            if raw_entity.get('entity','') == "attribute":
                attribute = raw_entity.get('value','')
            if raw_entity.get('entity','') == "thing":
                thing = raw_entity.get('value','')
            if raw_entity.get('entity','') == "place":
                thing = raw_entity.get('value','')
            if raw_entity.get('entity','') == "person":
                thing = raw_entity.get('value','')
                
        site = tracker.current_state().get('sender_id')        
        if len(attribute) > 0 and len(thing) > 0:
            publish('hermod/'+site+'/tts/say',{"text":"Looking now"})
            publish('hermod/'+site+'/display/startwaiting',{})
            result = self.lookup(attribute,thing)
            if result and len(result) > 0:
                dispatcher.utter_message(text="The "+attribute+" of "+thing+" is "+ result)
                # TODO send hermod/XX/display/url  {'url':'https://en.wiktionary.org/wiki/'+word} 
            else:
                dispatcher.utter_message(text="I don't know the "+attribute+" of "+thing)
        elif  len(attribute) > 0:
            dispatcher.utter_message(text="I didn't hear your question. Try again")
        elif  len(thing) > 0:
            dispatcher.utter_message(text="What do you want to know about "+thing)
        else:
            dispatcher.utter_message(text="I didn't hear your question. Try again")
        publish('hermod/'+site+'/display/stopwaiting',{})
        slotsets = []
        return slotsets
    
    def lookup_id(self,thing):
        API_ENDPOINT = "https://www.wikidata.org/w/api.php"
        params = {'action': 'wbsearchentities','format': 'json','language': 'en','search': thing}
        r = requests.get(API_ENDPOINT, params = params)
        results = r.json()['search']
        #print(results)
        final = None
        if len(results) > 0:
            final = r.json()['search'][0].get('id',None)
        return final
        
    def strip_after_bracket(self,text):
        parts = text.split("(")
        return parts[0]
            
    
    def lookup(self,attribute,thing):
        logger = logging.getLogger(__name__)    
        logger.debug(['lookup',attribute,thing]) 
        wikidata_id = self.lookup_id(thing)
        # client = Client()  # doctest: +SKIP
        # entity = client.get(wikidata_id, load=True)
        #logger.debug(json.dumps(entity))
        page = wptools.page(wikibase=wikidata_id)
        page.wanted_labels(list(self.wikidata_attributes.get('person').keys()) + list(self.wikidata_attributes.get('place').keys()))
        page.get_wikidata()
        facts = page.data['wikidata']
        clean_facts = {}
        for fact in facts:
            clean_key = self.strip_after_bracket(fact).lower().strip()
            # convert to single string, different types of facts - string, list, list of objects
            if type(facts[fact]) == str:
                # simple case string fact
                clean_facts[clean_key] = self.strip_after_bracket(facts[fact])
            elif type(facts[fact]) == list:
                # assume all list elements same type, decide based on first
                if len(facts[fact]) > 0:
                    if type(facts[fact][0]) == str:
                        # join first five with commas
                        max_list_facts=5
                        # only use the first listed capital 
                        if clean_key == "capital" or clean_key == "continent":
                            max_list_facts=1
                        
                        i = 0
                        joined_facts = []
                        for fact_item in facts[fact]:
                            if i < max_list_facts:
                                joined_facts.append(self.strip_after_bracket(fact_item))
                            else:
                                break
                            i = i+1
                                                        
                        clean_facts[clean_key] = ", ".join(joined_facts)
                            
                    elif type(facts[fact][0]) == dict:
                        # if list object has amount attribute, use amount from first list item
                        if 'amount' in facts[fact][0]:
                            clean_facts[clean_key] = facts[fact][0].get('amount','')
                        
        
        logger.debug(clean_facts)    
        if attribute.lower() in clean_facts:
            return clean_facts[attribute.lower()]
        return ""

        
class ActionSearchWikidataPerson(ActionSearchWikidata):
    def name(self) -> Text:
        return "action_search_wikidata_person"
    
class ActionSearchWikidataPlace(ActionSearchWikidata):
    def name(self) -> Text:
        return "action_search_wikidata_place"
        
class ActionSearchWikidataFollowup(ActionSearchWikidata):
    def name(self) -> Text:
        return "action_search_wikidata_followup"



class ActionSpellWord(Action):
    def name(self) -> Text:
        return "action_spell_word"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        logger = logging.getLogger(__name__)    
        logger.debug('SPELL WORD')
        last_entities = tracker.current_state()['latest_message']['entities']
        logger.debug(last_entities)
        word = ''
        for raw_entity in last_entities:
            logger.debug(raw_entity)
            if raw_entity.get('entity','') == "word":
                word = raw_entity.get('value','')
        if len(word) > 0:
            letters = []
            for letter in word:
                letters.append(letter.upper())
            message = word + " is spelled "+", ".join(letters)
            dispatcher.utter_message(text=message)
        else:
            dispatcher.utter_message(text="I didn't hear the word you want to spell. Try again")
       
        slotsets = []
        return slotsets  
