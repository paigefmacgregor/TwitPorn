import helpers
# print a table showing the total number of tweets for each screen name after 1/1/2013
helpers.total_tweets(print_table=True, begin_date='1/1/2013')

# export a csv file called 'tweetsperday' showing tweets per day
helpers.tweets_per_day(export_csv='tweetsperday')

# export a csv file called 'twitporn' containing virtually all data in twitporn database
helpers.all_tweet_data('twitporn')