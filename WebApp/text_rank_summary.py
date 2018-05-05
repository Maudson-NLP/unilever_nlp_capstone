"""Python implementation of the TextRank algoritm.

From this paper:
    https://web.eecs.umich.edu/~mihalcea/papers/mihalcea.emnlp04.pdf

Based on:
    https://gist.github.com/voidfiles/1646117
    https://github.com/davidadamojr/TextRank

Todo: This is slow
"""
import io
import itertools
import networkx as nx
import nltk
import os


def filter_for_tags(tagged, tags=['NN', 'JJ', 'NNP']):
    """Apply syntactic filters based on POS tags."""
    return [item for item in tagged if item[1] in tags]


def normalize(tagged):
    """Return a list of tuples with the first item's periods removed."""
    return [(item[0].replace('.', ''), item[1]) for item in tagged]


def unique_everseen(iterable, key=None):
    """List unique elements in order of appearance.

    Examples:
        unique_everseen('AAAABBBCCDAABBB') --> A B C D
        unique_everseen('ABBCcAD', str.lower) --> A B C D
    """
    seen = set()
    seen_add = seen.add
    if key is None:
        for element in [x for x in iterable if x not in seen]:
            seen_add(element)
            yield element
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                yield element


def levenshtein_distance(first, second):
    """Return the Levenshtein distance between two strings.

    Based on:
        http://rosettacode.org/wiki/Levenshtein_distance#Python
    """
    if len(first) > len(second):
        first, second = second, first
    distances = range(len(first) + 1)
    for index2, char2 in enumerate(second):
        new_distances = [index2 + 1]
        for index1, char1 in enumerate(first):
            if char1 == char2:
                new_distances.append(distances[index1])
            else:
                new_distances.append(1 + min((distances[index1],
                                             distances[index1 + 1],
                                             new_distances[-1])))
        distances = new_distances
    return distances[-1]


def build_graph(nodes):
    """Return a networkx graph instance.

    :param nodes: List of hashables that represent the nodes of a graph.
    """
    gr = nx.Graph()  # initialize an undirected graph
    gr.add_nodes_from(nodes)
    nodePairs = list(itertools.combinations(nodes, 2))

    # add edges to the graph (weighted by Levenshtein distance)
    for pair in nodePairs:
        firstString = pair[0]
        secondString = pair[1]
        levDistance = levenshtein_distance(firstString, secondString)
        gr.add_edge(firstString, secondString, weight=levDistance)

    return gr

def extractKeyphrases(text,top_n):
    # tokenize the text using nltk
    wordTokens = nltk.word_tokenize(text)
    print("Tokenized Words")
    # assign POS tags to the words in the text
    tagged = nltk.pos_tag(wordTokens)
    textlist = [x[0] for x in tagged]
    print("Pos Tagging")

    tagged = filter_for_tags(tagged)
    tagged = normalize(tagged)

    unique_word_set = unique_everseen([x[0] for x in tagged])
    word_set_list = list(unique_word_set)

    # this will be used to determine adjacent words in order to construct keyphrases with two words

    graph = build_graph(word_set_list)
    print("Graph Builded")

    # pageRank - initial value of 1.0, error tolerance of 0,0001,
    calculated_page_rank = nx.pagerank(graph, weight='weight')
    print("")
    # most important words in ascending order of importance
    keyphrases = sorted(calculated_page_rank, key=calculated_page_rank.get, reverse=True)

    # the number of keyphrases returned will be relative to the size of the text (a third of the number of vertices)
    aThird = int(len(word_set_list) / 3)
    keyphrases = keyphrases[0:aThird + 1]

    # take keyphrases with multiple words into consideration as done in the paper - if two words are adjacent in the text and are selected as keywords, join them
    # together
    modifiedKeyphrases = set([])
    dealtWith = set([])  # keeps track of individual keywords that have been joined to form a keyphrase
    i = 0
    j = 1
    while j < len(textlist):
        firstWord = textlist[i]
        secondWord = textlist[j]
        if firstWord in keyphrases and secondWord in keyphrases:
            keyphrase = firstWord + ' ' + secondWord
            modifiedKeyphrases.add(keyphrase)
            dealtWith.add(firstWord)
            dealtWith.add(secondWord)
        else:
            if firstWord in keyphrases and firstWord not in dealtWith:
                modifiedKeyphrases.add(firstWord)

            # if this is the last word in the text, and it is a keyword,
            # it definitely has no chance of being a keyphrase at this point
            if j == len(textlist) - 1 and secondWord in keyphrases and secondWord not in dealtWith:
                modifiedKeyphrases.add(secondWord)

        i = i + 1
        j = j + 1

    result=list(modifiedKeyphrases)
    if top_n>len(result):
        return_result=result
    else:
        return_result=result[0:top_n]

    return return_result

def extract_sentences(text, summary_length=100, clean_sentences=False):
    """Return a paragraph formatted summary of the source text.

    :param text: A string.
    """
    print (1)
    sent_detector = nltk.data.load('tokenizers/punkt/english.pickle')
    sentence_tokens = sent_detector.tokenize(text.strip())
    graph = build_graph(sentence_tokens)
    print (graph)

    calculated_page_rank = nx.pagerank(graph, weight='weight')

    # most important sentences in ascending order of importance
    sentences = sorted(calculated_page_rank, key=calculated_page_rank.get,
                       reverse=True)

    # return a 100 word summary
    summary = ' '.join(sentences)
    # print (summary)
    # summary_words = summary.split()
    # summary_words = summary_words[0:summary_length]
    # dot_indices = [idx for idx, word in enumerate(summary_words) if word.find('.') != -1]
    # if clean_sentences and dot_indices:
    #     last_dot = max(dot_indices) + 1
    #     summary = ' '.join(summary_words[0:last_dot])
    # else:
    #     summary = ' '.join(summary_words)
    # res = ""
    # number_of_sentence = summary.count(".")
    # number_of_summary_sentence = number_of_sentence / 2
    # if number_of_summary_sentence == 0:
    #     number_of_summary_sentence = 1
    # count = 0
    # while count < number_of_summary_sentence:
    #     res += summary[:summary.find(".") + 1]
    #     summary = summary[summary.find(".") + 1:]
    #     count += 1
    # print (res)
    summary = ' '.join(sentences)
    summaryWords = summary.split()
    summaryWords = summaryWords[0:101]
    summary = ' '.join(summaryWords)
    return summary


def write_files(summary, key_phrases, filename):
    """Write key phrases and summaries to a file."""
    print("Generating output to " + 'keywords/' + filename)
    key_phrase_file = io.open('keywords/' + filename, 'w')
    for key_phrase in key_phrases:
        key_phrase_file.write(key_phrase + '\n')
    key_phrase_file.close()

    print("Generating output to " + 'summaries/' + filename)
    summary_file = io.open('summaries/' + filename, 'w')
    summary_file.write(summary)
    summary_file.close()

    print("-")


# def summarize_all():
#     # retrieve each of the articles
#     end_sentence = 0
#     res_list = []
#     articles = os.listdir("training")
#     for article in articles:
#         print('Reading articles/' + article)
#         article_file = io.open('training/' + article, 'r')
#         text = article_file.read()
#         summary = extract_sentences(text)
#         res = ""
#         number_of_sentence = summary.count(".")
#         number_of_summary_sentence = number_of_sentence/3
#         if number_of_summary_sentence == 0:
#             number_of_summary_sentence = 1
#         count = 0
#         while count < number_of_summary_sentence:
#             res += summary[:summary.find(".")+1]
#             summary = summary[summary.find(".")+1:]
#             count += 1
#         print res
#         res_list.append(res)
#     return res_list
#         ###write_files(summary, keyphrases, article)
#
# summarize_all()
