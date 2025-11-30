#!/usr/bin/python
import subprocess
print("Ollama:", subprocess.run(['which', 'ollama'], capture_output=True, text=True).stdout, "Python:", subprocess.run(['which', 'python'], capture_output=True, text=True).stdout)
import time
import json
import os
import ollama

def gen_replies(recent_text):
    with open('config.json', 'r') as file:
        config = json.load(file)
    system_prompt =  f"""You are {config['name']}. {config['name']} was asked about their personality so take notes and form a base tone of {config['name']}: "{config['personalDescription']}" You have {len(config['moods'])} moods. Your moods are: {{{", ".join(f'"{mood}": "{config['moods'][mood]}"' for mood in config['moods'])}}}. As {config['name']}, you will be given new texts from a sender. You MUST output **EXACTLY {len(config['moods'])} RESPONSES**. Each text response should be a response as though you were in the given mood. If moods were {{"Happy": "Very nice and upbeat.", "Sad": "Very short and pessimistic", "Angry": "Quick to snap and not very nice"}} and the text was "Hi", you respond with {{"Happy": "Hi! How are you, is everything good?", "Sad": "Hey, how are you? I'm hanging in there...", "Angry": "Yeah, what do you need?"}}. The goal is to always return a dictionary and the dictionary must have {len(config['moods'])} entries."""
    tries = 5
    while tries > 0:
        out = ollama.chat(
            model="llama3.1:8b",
            format="json",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": recent_text}
            ]
        )["message"]["content"]
        out = json.loads(out)
        if [mood for mood in sorted(out)] == [mood for mood in sorted(config['moods'])]:
            return out
        tries -= 1
        print("[GENERATING] Retry.\n")
    fallback = {}
    for mood in config['moods']:
        fallback[mood] = ""
    return fallback

if __name__=='__main__':
    with open('config.json', 'r') as file:
        config = json.load(file)
    print("[INIT] Config loaded.\n")
    recent_text = ""
    recent_number = ""
    path = "/Users/"+os.getenv('USER')+"/Library/Messages/chat.db"
    print("[INIT] Texts found.\n")
    while True:
        if subprocess.run(['sqlite3', path, 'SELECT is_from_me FROM message ORDER BY date DESC LIMIT 1;'], capture_output=True, text=True).stdout.strip() == "1":
           print("[WAITING] User sent most recent message ...\n")
           time.sleep(3)
           continue
        text = ""
        while len(text)==0:
           print("[WAITING] Finding text ...\n")
           time.sleep(3)
           text = (subprocess.run(['sqlite3', path, 'SELECT text FROM message ORDER BY date DESC LIMIT 1;'], capture_output=True, text=True).stdout).strip()
        number = (subprocess.run(['sqlite3', path, 'SELECT id FROM handle WHERE ROWID=(SELECT handle_id FROM message ORDER BY date DESC LIMIT 1);'], capture_output=True, text=True).stdout).strip()
        with open('config.json', 'r') as file:
            config = json.load(file)
        print("Text:", text, " | Number:", number, " | Config:", config['phoneListMode'], " | Phone Numbers:", config['phoneNumbers'])
        if ((config['phoneListMode'] == 'Include' and number in config['phoneNumbers']) or (config['phoneListMode'] == 'Exclude' and number not in config['phoneNumbers'])) and (recent_text != text or recent_number != number):
            recent_text = text
            recent_number = number
            replies = {'Reply': "Refresh"}
            print(f"[RUN] New text from {recent_number} found.\n")
            while replies.get('Reply')=="Refresh": 
                print(f"[GENERATING] {len(config['moods'])} new responses will be generated.\n")
                start = time.time()
                replies = gen_replies(recent_text)
                end = time.time()
                print(f"[FINISH] Done generating in {str(end-start)} seconds.\n")
                replies.update({'Reply': "", 'sender': recent_number, 'message': recent_text, 'time': str(end-start)})
                with open('replies.json', 'w') as json_file:
                    print("[WRITING] Writing to replies.json.\n")
                    json.dump(replies, json_file, indent=4)
                print("[WAITING] User input...\n")
                while replies.get('Reply')=="":
                    with open('replies.json', 'r') as json_file:
                        data = json.load(json_file)
                        replies['Reply'] = data['Reply']
            if replies.get('Reply')=="Ignore":
                print("[FINISH] Not sending text.\n")
            else:
                print("[FINISH] Sending text.\n")
                os.system('osascript send_imessage.applescript {} "{}"'.format(recent_number, replies[replies['Reply']]))
         
