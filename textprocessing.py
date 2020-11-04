#!/usr/bin/python

import imaplib
import email

import nltk
import webbrowser

from collections import defaultdict
from operator import itemgetter
from multiprocessing import Pool


username = "usesrname@gmail.com"
password = "pwd"
server = "imap.gmail.com"
folder = "INBOX"

google_graph = """
<html>
  <head>
    <script type="text/javascript" src="https://www.google.com/jsapi"></script>
    <script type="text/javascript">
      google.load('visualization', '1', {'packages':['corechart']});
      google.setOnLoadCallback(drawChart);

      function drawChart() {
        var data = new google.visualization.DataTable();
        data.addColumn('string', 'Phrases in your email');
        data.addColumn('number', 'Frequency');
        data.addRows(%s
        );

        var chart = new google.visualization.PieChart(document.getElementById('chart_div'));
        chart.draw(data, {width: 1200, height: 1200, is3D: true, title: 'Phrases in your email'});
      }
    </script>
  </head>

  <body>
    <div id="chart_div"></div>
  </body>
</html>


"""


def auth_email():                                              #Authenticate email -- can use external apps token if business mails are used
    base_email=imaplib.IMAP4_SSL(server, 993)
    base_email.login(username,password)
    base_email.select(folder)
    tag, count = base_email.search(None, 'ALL')
    try:
        for num in count[0].split():
            tag, data = base_email.fetch(num, '(RFC822)')
            yield email.message_from_bytes(data[0][1])
    finally:
        base_email.close()
        base_email.logout()

def read_textfrommail(words):                                #Read words from the email text
    for message in words:
        for word in message.walk():
            if word.get_content_type() == "text/plain":
                yield word

def transformation(words):                                        #transform the words by tokenizeing and tagging them
    for word in words:
        sentences = nltk.sent_tokenize(str(word))
        sentences = [nltk.word_tokenize(sent) for sent in sentences]
        sentences = [nltk.pos_tag(sent) for sent in sentences]
        yield sentences

def phrases_in_email(words):                               #Finds phrases in the email text
    for message in words:
        for sentence in message:
            for (w1,t1), (w2,t2), (w3,t3) in nltk.trigrams(sentence):
                if (t1.startswith('V') and t2 == 'TO' and t3.startswith('V')):
                    yield ((w1,w2,w3), 1)

def mapping_word():
    words = auth_email()
    text_words = read_textfrommail(words)
    transformed = transformation(text_words)
    for item,count in phrases_in_email(transformed):
        yield item, count

def words_partition(phrases):
    partitioned_word = defaultdict(list)
    for phrase, count in phrases:
        partitioned_word[phrase].append(count)
    return partitioned_word.items()

def reducer(phrase_key_val):
    phrase, count = phrase_key_val
    return [phrase, sum(count)]

def start_mr(mapper_func, reducer_func, processes=1):
    pool = Pool(processes)
    map_output = mapper_func()
    partitioned_word = words_partition(map_output)
    reduced_output = pool.map(reducer_func, partitioned_word)
    return reduced_output

def export_html_graph(sort_list, num=15):
    results = []
    for items in sort_list[0:num]:
        phrase = " ".join(items[0])
        result = [phrase, items[1]]
        results.append(result)
    page = google_graph % results
    f = open('results.html','wb')          #html file to report the results
    f.write(page.encode())
    f.close()

    filename = 'file:///Users/mac/Documents/Github/EmailTextProcessing/' + 'results.html' 
    webbrowser.open_new_tab(filename)       #Open the file to check the results

def text_processing():
    processed_texts = start_mr(mapping_word, reducer)
    sorted_processed_texts = sorted(processed_texts, key=itemgetter(1), reverse=True)
    export_html_graph(sorted_processed_texts)

if __name__ == "__main__":
    text_processing()
