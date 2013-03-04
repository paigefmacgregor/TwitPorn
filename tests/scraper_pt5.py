# import all the libraries we're using
import time, pprint, re
from datetime import datetime
import pymongo, tweepy

# a function for replacing unicode characters with ascii
def ascii_encode(text):
    text = text.replace(u'\u2019',u'\'').replace(u'\u0160',u'')
    text = text.replace(u'\u8211',u'-').replace(u'\u8220',u'"').replace(u'\u8221',u'"')
    text = text.replace(u'\u201c',u'"').replace(u'\u201d',u'"')
    text.encode('ascii','ignore')
    return text

try:
    # connect to Mongo database
    connection = pymongo.Connection()
    db = connection.twitporn
    print "ready to scrape some tweets!"

    # ask the user for a date
    date_string = raw_input("input starting date in mm/dd/yyyy format: ");
    date_list = date_string.split('/')
    start_date = datetime(int(date_list[2]), int(date_list[0]), int(date_list[1]))
    print "start date:", start_date

    # ask user to confirm the date is correct
    confirm = raw_input("that's " + str((datetime.now() - start_date).days) + " days of tweets, are you sure? (y/n): ")
    if confirm != 'y':
        exit()

    # a list of usernames to get twitter updates from
    usernames = ['itstessalane', 'tommygunnxxx', 'tommypistol', 'trinitystclair', 'xcorvus777']
    # go through each of the names...
    for name in usernames:
        print "GETTING TWEETS FOR", name
        is_done = False
        page = 1
        # and use tweepy to get last 1000 tweets from the name's timeline
        while not is_done:
            print "GETTING", name, "PAGE", page
            try:
                tweets = tweepy.api.user_timeline(screen_name=name, count=1000, include_rts=1, include_entities=1, page=page)
            except tweepy.error.TweepError:
                print "TWEEPY ERROR... retrying in 30 seconds"
                time.sleep(30)
                tweets = tweepy.api.user_timeline(screen_name=name, count=1000, include_rts=1, include_entities=1, page=page)

            # go through each of their tweets...
            for tweet in tweets:
                # see if tweet date falls before start date...
                start_date_diff = tweet.created_at - start_date
                if start_date_diff.days < 0: 
                    # if so, we're done, so break out of loop
                    is_done = True
                    break
                print "tweet date:", tweet.created_at, ",", start_date_diff.days, "days after start date"
                print tweet.author.screen_name, ': "', tweet.text, '"'

                # make a tweet object with all the info we want to save about tweet
                tweet_text = ascii_encode(tweet.text)
                
                tweet_object = {
                    '_id': tweet.id_str,
                    
                    'author': {
                        'name': tweet.author.name,
                        'screen_name': tweet.author.screen_name.lower(),
                        'followers_count': tweet.author.followers_count,
                        'friends_count': tweet.author.friends_count,
                    },
                    'text': tweet_text,
                    'words': re.sub('[^a-zA-Z0-9_\-@# ]', '', tweet_text).lower().split(),
                    'created_at': tweet.created_at,
                    
                    'retweet_count': tweet.retweet_count,
                    'truncated': tweet.truncated,
                    'favorited': tweet.favorited,
                    
                    'entities': tweet.entities
                }
                
                # get retweet status if it exists
                try:
                    retweeted_status = tweet.retweeted_status
                    tweet_object['is_retweet'] = True
                    tweet_object['retweeted_from'] = retweeted_status.author.screen_name
                except AttributeError:
                    tweet_object['is_retweet'] = False
                    tweet_object['retweeted_from'] = False
                
                #print tweet.text
                # insert the object in a database collection called tweets
                db.tweets.insert(tweet_object)

            if not is_done:
                # wait for 30 seconds to avoid hitting Twitter API rate limit
                print "not done yet... need another page"
                page = page + 1
                print db.tweets.find({'author.screen_name': name}).count(), "total", name, "tweets in database"
                print "waiting 30 seconds until next request..."
                time.sleep(30)

        print "got all tweets for", name, "since", start_date
        print db.tweets.find({'author.screen_name': name}).count(), "total", name, "tweets in database"
        # if this wasn't the last username, wait for 30 secs before requesting next username
        if name != usernames[-1]:
            print "waiting 30 seconds until next request..."
            time.sleep(30)
    
    # count the number of tweets in database and print it
    tweet_count = db.tweets.count()
    print "TWEETS COLLECTION IN DATABASE CONTAINS", tweet_count, "TWEETS"

except pymongo.errors.AutoReconnect:
    print "ERROR CONNECTING TO DATABASE! Is mongod running?"





import csv, copy
from pprint import pprint
from datetime import datetime
from inspect import getargspec
from decorator import decorator
from prettytable import PrettyTable

"""
    This module contains decorators used by the functions in helpers.py
    """
@decorator
def date_range(f, *args, **kwargs):
    begin_date = kwarg_lookup('begin_date', f, args)
    end_date = kwarg_lookup('end_date', f, args)
    extend_query_index = kwarg_index('extend_query', f, args)
    
    if (begin_date or end_date) and extend_query_index:
        date_query = {'created_at': {}}
        
        if begin_date:
            # parse date if it's a string
            if type(begin_date) is str:
                date_list = begin_date.split('/')
                begin_date = datetime(int(date_list[2]), int(date_list[0]), int(date_list[1]))
            # add to date query
            date_query['created_at']['$gte'] = begin_date
        
        if end_date:
            # parse date if it's a string
            if type(end_date) is str:
                date_list = end_date.split('/')
                end_date = datetime(int(date_list[2]), int(date_list[0]), int(date_list[1]))
            # add to date query
            date_query['created_at']['$lte'] = end_date
        
        # add the date range to the extend_query keyword argument
        extend_query = dict(args[extend_query_index].items() + date_query.items())
        # by slicing it into the args tuple :P
        args = args[:extend_query_index] + (extend_query,) + args[extend_query_index+1:]
    
    result = f(*args, **kwargs)
    return result

@decorator
def export_csv(f, *args, **kwargs):
    result = f(*args, **kwargs)
    
    filename = kwarg_lookup('export_csv', f, args)
    if filename and type(result) is list and len(result):
        # if passed a 1D array, make a 2D array with 1 item/line
        result_copy = False
        if type(result[0]) is not list:
            result_copy = [[row] for row in result]
        else:
            result_copy = result
        # create CSV file
        new_file = open(filename + '.csv','wb')
        csv_writer = csv.writer(new_file)
        for row in result_copy:
            csv_writer.writerow(row)
        new_file.close()

    return result

@decorator
def print_table(f, *args, **kwargs):
    result = f(*args, **kwargs)
    
    print_table = kwarg_lookup('print_table', f, args)
    if print_table and type(result) is list and len(result):
        # if passed a 1D array, make a 2D array with 1 item/line
        result_copy = False
        if type(result[0]) is not list:
            result_copy = [[row] for row in result]
        else:
            result_copy = result
        # create and print pretty table
        table = PrettyTable(result_copy[0])
        for row in result_copy[1:]:
            table.add_row(row)
        print table

    return result

@decorator
def should_return(f, *args, **kwargs):
    result = f(*args, **kwargs)
    # conditional return
    should_return = kwarg_lookup('should_return', f, args)
    if(should_return):
        return result
    else:
        return

def kwarg_lookup(keyword, func, args):
    try:
        return args[getargspec(func).args.index(keyword)]
    except:
        return False

def kwarg_index(keyword, func, args):
    try:
        return getargspec(func).args.index(keyword)
    except:
        return False



import pymongo, csv, operator
from datetime import datetime
from pprint import pprint

from helper_decorators import date_range, export_csv, print_table, should_return

connection = False
db = False
try:
    connection = pymongo.Connection()
    db = connection.twitporn
except pymongo.errors.AutoReconnect:
    print "ERROR CONNECTING TO DATABASE! Is mongod running?"

@should_return
@export_csv
@print_table
def screen_names_in_db(print_table=False, export_csv=False, should_return=True):
    """
        Returns a list of all distinct Twitter screen names in the database.
        """
    return db.tweets.distinct('author.screen_name')

@should_return
@export_csv
@print_table
@date_range
def total_tweets(begin_date=False, end_date=False, extend_query={}, print_table=True, export_csv=False, should_return=False):
    """
        Prints the total number of tweets for each screen name in the database.
        """
    export_data = [['name', '# of tweets']]
    
    for name in screen_names_in_db():
        query = dict({'author.screen_name': name}.items() + extend_query.items())
        export_data.append([name, db.tweets.find(query).count()])
    
    export_data.append(['TOTAL', db.tweets.find(extend_query).count()])
    return export_data

@should_return
@export_csv
@print_table
@date_range
def tweets_per_day(begin_date=False, end_date=False, extend_query={}, print_table=True, export_csv=False, should_return=False):
    """
        Prints the average number of tweets per day for each screen name in database.
        """
    export_data = [['screen name', 'average # tweets per day']]
    
    """
        for name in screen_names_in_db():
        query = dict({'author.screen_name': name}.items() + extend_query.items())
        tweets = db.tweets.find(query).sort('created_at', pymongo.ASCENDING)
        if tweets.count():
            first_date = tweets[0]['created_at']
            diff_days = (datetime.now() - first_date).days
            total = db.tweets.find(query).count()
            avg = float(total) / float(diff_days)
            export_data.append([name, avg])
        else:
            export_data.append([name, 0])
            """
    return export_data

@should_return
@export_csv
@print_table
@date_range
def tweets_with_word(words, begin_date=False, end_date=False, extend_query={}, print_table=True, export_csv=False, should_return=False):
    """
        Prints the number of tweets containing a given word or list of words for each screen name in database.
        """
    if type(words) is str: words = [words]
    words_string = " OR ".join(words)
    export_data = [['screen name', '# of tweets containing ' + words_string]]
    
    for name in screen_names_in_db():
        query = dict({'words': {'$in': words}, 'author.screen_name': name}.items() + extend_query.items())
        tweet_count = db.tweets.find(query).count()
        export_data.append([name, tweet_count])
    
    return export_data

@should_return
@export_csv
@print_table
@date_range
def entity_frequency(entity_type, min_count=1, begin_date=False, end_date=False, extend_query={}, print_table=True, export_csv=False, should_return=False):
    """
        For each screen name in the database, counts the frequencies of the most commonly tweeted entities by a particular user.
        
        eg. helpers.entity_frequency('urls')
        returns the most commonly tweeted urls for each screen name, sorted by frequency of use.
        Valid entity types are 'user_mentions', 'hashtags', and 'urls'.
        
    entity_fields = {'user_mentions': 'screen_name', 'hashtags': 'text', 'urls': 'expanded_url'}
    if entity_type not in entity_fields:
        print "ERROR: Invalid entity type. Valid types are 'user_mentions', 'hashtags', and 'urls'"
            """
    export_data = [['screen name', entity_type[:-1], '# of mentions']]
    
    for name in screen_names_in_db():
        entity_counts = {}
        query = dict({'author.screen_name':name}.items() + extend_query.items())
        for tweet in db.tweets.find(query):
            for entity in tweet['entities'][entity_type]:
                entity_string = entity[entity_fields[entity_type]].lower()
                if entity_string in entity_counts:
                    entity_counts[entity_string] += 1
                else:
                    entity_counts[entity_string] = 1
        
        # iterate through link counts dict, sorted by values
        for entity_count in sorted(entity_counts.iteritems(), key=operator.itemgetter(1), reverse=True):
            if entity_count[1] >= min_count:
                export_data.append([name, entity_count[0], entity_count[1]])
    
    return export_data

@should_return
@export_csv
@print_table
@date_range
def word_frequency(min_count=10, begin_date=False, end_date=False, extend_query={}, print_table=True, export_csv=False, should_return=False):
    """
        For each screen name in the database, counts the frequency of words used and prints them in order of frequency.
        
        By default, the following frequently occurring words are filtered out of this analysis:
        ['the','to','in','of','and','for','is','on','at','a','be','it','that','this','with','are','if','its','by']
        """
    filtered_words = ['the','to','in','of','and','for','is','on','at','a','be','it','that','this','with','are','if','its','by']
    export_data = [['screen name', 'word', '# of times used', 'occurrence per tweet']]
    
    for name in screen_names_in_db():
        word_counts = {}
        query = dict({'author.screen_name':name}.items() + extend_query.items())
        total_tweets = db.tweets.find(query).count()
        for tweet in db.tweets.find(query):
            for word in tweet['words']:
                if word in filtered_words: continue
                if word in word_counts:
                    word_counts[word] += 1
                else:
                    word_counts[word] = 1
        
        # iterate through link counts dict, sorted by values
        for word_counts in sorted(word_counts.iteritems(), key=operator.itemgetter(1), reverse=True):
            if word_counts[1] >= min_count:
                export_data.append([name, word_counts[0], word_counts[1], (float(word_counts[1]) / float(total_tweets))])
    
    return export_data

@should_return
@export_csv
@print_table
@date_range
def tweets_text(begin_date=False, end_date=False, extend_query={}, print_table=True, export_csv=False, should_return=False):
    """
        Prints the text of all tweets in the database.
        """
    export_data = [['screen_name', 'date sent', 'tweet text']]
    for name in screen_names_in_db():
        query = dict({'author.screen_name': name}.items() + extend_query.items())
        for tweet in db.tweets.find(query):
            tweet_text = unicode(tweet['text']).encode('ascii','ignore')
            export_data.append([name, tweet['created_at'], tweet_text])
    return export_data

def all_tweet_data(filename):
    """
        Exports a CSV file containing nearly all known data about all tweets in the database.
        
        Leaves out a few details about entities.
        """
    # make a new csv file with name of filename
    new_file = open(filename+'.csv','wb')
    # open the file with csv writer
    csv_file = csv.writer(new_file)
    
    # first row of csv is a list of the keys for all the data columns
    tweet_keys = _recursive_list(db.tweets.find_one(), [], ['words', 'entities'], True)
    entity_types = [['user_mentions','screen_name'], ['hashtags','text'], ['urls','expanded_url']]
    for entity_type in entity_types:
        tweet_keys.append(entity_type[0] + ' count')
        tweet_keys.append(entity_type[0])
    csv_file.writerow([unicode(field).encode('ascii','ignore') for field in tweet_keys])
    
    for tweet in db.tweets.find().sort('author.screen_name', pymongo.ASCENDING):
        # get basic fields
        tweet_fields = _recursive_list(tweet, [], ['words', 'entities'], False)
        # get limited data about entities
        for entity_type in entity_types:
            # get count for each type of entity
            entities = tweet['entities'][entity_type[0]]
            tweet_fields.append(len(entities))
            # and construct a stringified list of the entities' representative strings
            entity_strings = []
            for entity in entities:
                entity_strings.append(str(entity[entity_type[1]]))
            joined_entities = ', '.join(entity_strings)
            tweet_fields.append(joined_entities)
        
        csv_file.writerow([unicode(field).encode('ascii','ignore') for field in tweet_fields])
    
    new_file.close()

def _recursive_list(data, list_so_far, keys_to_ignore, is_key_list):
    if type(data) is dict:
        for key, val in data.iteritems():
            if key in keys_to_ignore:
                continue
            
            if type(val) is dict or type(val) is list:
                _recursive_list(val, list_so_far, keys_to_ignore, is_key_list)
            else:
                item = key if is_key_list else val
                list_so_far.append(item)
    
    elif type(data) is list:
        list_so_far.append(str(data))
    
    return list_so_far

def remove_all_tweets():
    """
        Removes all tweets from the database. Cannot be undone.
        """
    confirm = raw_input("this will remove all tweets from your database, are you sure? (y/n): ")
    if confirm != 'y':
        return
    db.tweets.remove()
    print db.tweets.count(), "total tweets in database"


import helpers
# print a table showing the total number of tweets for each screen name sent after 1/1/2013
helpers.total_tweets(print_table=True, begin_date='1/1/2013')

# export a csv file called 'tweetsperday' showing tweets per day
helpers.tweets_per_day(export_csv='tweetsperday')

# export a csv file called 'twitporn' containing virtually all data in twitporn database
helpers.all_tweet_data('twitporn_pt4')