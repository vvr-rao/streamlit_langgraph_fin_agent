import streamlit as st


st.set_page_config(layout="wide")

st.markdown("""
        <style>
               .block-container {
                    padding-top: 0rem;
                    padding-bottom: 3rem;
                    padding-left: 2rem;
                    padding-right: 2rem;
                }
        </style>
        """, unsafe_allow_html=True)

st.write("\n\n\n")
st.title('Simple Stock Market Research Agent')


###################
###Define Tools###
import yfinance as yf

def get_stock_details(ticker: str) -> str:
    """Gets the details of a stock from Yahoo finance including current price, previous close, 52 week range, a summary of the business and things like the address and industry

    Args:
        ticker: ticker str
    """
    # """This is a tool for getting the price of a stock when passed a ticker symbol"""
    stock = yf.Ticker(ticker)

    summary = f"""
    Here is a summary of the stock {ticker} for today:

    PRICE DETAILS:
    Current Stock Price: {stock.info['currentPrice']}
    Previous Close: {stock.info['previousClose']}
    Open today: {stock.info['open']}
    52 Week Range: {stock.info['fiftyTwoWeekRange']}
    Target High Price: {stock.info['targetHighPrice']}
    Target Low Price: {stock.info['targetLowPrice']}
    Target Mean Price: {stock.info['targetMeanPrice']}

    VOLUME DETAILS:
    Volume today: {stock.info['volume']}
    Average Daily Volume 10 Days: {stock.info['averageDailyVolume10Day']}
    SHares Short: {stock.info['sharesShort']}
    Shares Short Prior Month: {stock.info['sharesShortPriorMonth']}

    BUSINESS PRFILE:
    Summary: {stock.info['longBusinessSummary']}
    Sector: {stock.info['sector']}
    Industry: {stock.info['industry']}
    Country: {stock.info['country']}

    """

    return summary

def get_stock_news(ticker: str) -> str:
    """Retrieves news related to a specific stock from Yahoo Finance. This can be used for a  web search for news items tied to a specific stock.

    Args:
        ticker: ticker str
    """
    # """This is a tool for getting the latest news tied to a stock when passed a ticker symbol"""
    stock = yf.Ticker(ticker)
    news_items = stock.news
    if len(news_items) > 5:
        news_items = news_items[:5]

    news_summaries = f"SUMMARIES OF TODAY's NEWS for {ticker}:\n"

    for i, item in enumerate(news_items, 1):  # Limit to first 5 news items
        news_summaries += f"Item {i} : {item['content']['summary']}\n"

    return news_summaries

from GoogleNews import GoogleNews
googlenews = GoogleNews(lang='en')

def web_search_news(search_term: str) -> str:
    """Does a web search for news on a term and returns a summary of the first 10 items. This can be used for a general web search for news without tying the search to a stock.

    Args:
        search_term: search_term str
    """
    # """This is a tool for retrieve the latest news about any item. You can get the news by passing a search term"""


    googlenews.search(search_term)
    results = googlenews.results(sort=True)
    #print(len(results))
    #if len(results) > 10:
    #        results = results[:10]

    news_summaries = f"HEADLINES OF WEB SEARCH FOR TERM for {search_term}:\n"

    for i, item in enumerate(results, 1):  # Limit to first 5 news items
        news_summaries += f"Item {i} : {item['desc']}\n"

    return news_summaries

import requests
from bs4 import BeautifulSoup

def web_search_general(search_term: str) -> str:
    """Does a general web search and provides a abstracts of the top results. Use this to find infomration on a subject.

    Args:
        search_term: search_term str
    """
    # """This is a tool to do a web search and retrieve information on a topic."""


    url = f"https://duckduckgo.com/html/?q={search_term}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    results = []
    for result in soup.select('.result'):
        #print(result)
        title = result.select_one('.result__title a')
        snippet = result.select_one('.result__snippet')
        if title and snippet:
            results.append({
                'title': title.get_text(strip=True),
                'link': title['href'],
                'snippet': snippet.get_text(strip=True)
            })
    

    # Example usage
    out = f"LIST OF ABSTRACTS for {search_term}\n"
    for i, res in enumerate(results):
        #print(f"Title: {res['title']}\nLink: {res['link']}\nSnippet: {res['snippet']}\n")
        out = out + f"Anstract {i}: {res['snippet']}\n"

    return(out)

###Set up Agent###

from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition # this is the checker for the if you got a tool back
from langgraph.prebuilt import ToolNode
#from IPython.display import Image, display
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Annotated, TypedDict
import operator
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition # this is the checker for the
from langgraph.prebuilt import ToolNode

from langchain_openai import ChatOpenAI
import os

# Retrieve API key from secrets
openai_api_key = st.secrets["OEPNAI_API_KEY"]

os.environ['OPENAI_API_KEY'] = openai_api_key

llm = ChatOpenAI(model="gpt-4o")

tools = [get_stock_details, get_stock_news, web_search_news, web_search_general]

llm_with_tools = llm.bind_tools(tools)

class GraphState(TypedDict):
    """State of the graph."""
    query: str
    finance: str
    final_answer: str
    # intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]
    messages: Annotated[list[AnyMessage], operator.add]

instruction = """You are a helpful assistant tasked with using a web search, the yahoo finance stock details search and a yahoo finance stock news search to answer question on stocks.
You will be asked for information on a company or companies or a stock or stocks.
You will need to use the tools provided to get as much information about the company/stock.
Relevant information would include, news about the markets the company operates in, news about the countries, competitor news, news abut key company personnel like the CEO.
Think long and hard about how you will use the tools. Look for information on the company and think of the latest developments in the world and how they might impact the company.
Also, retrieve any information of the company's industry and its competitors and look for any developments which might impactthe company.
Look for any regulatory changes as will and think about how they might impact the company.
Use your best judgment is searching for information but be thorough and answer the question asked utilizing all the tools at your disposal.
State any assumptions you are making any judgement calls you are making based on the information you retrieve.
    """

# Resoner Node
def reasoner(state):
    query = state["query"]
    messages = state["messages"]
    # System message
    sys_msg = SystemMessage(content=instruction)
    message = HumanMessage(content=query)
    messages.append(message)
    result = [llm_with_tools.invoke([sys_msg] + messages)]
    return {"messages":result}

# Graph
workflow = StateGraph(GraphState)

# Add Nodes
workflow.add_node("reasoner", reasoner)
workflow.add_node("tools", ToolNode(tools)) # for the tools

# Add Edges
workflow.add_edge(START, "reasoner")

workflow.add_conditional_edges(
    "reasoner",
    # If the latest message (result) from node reasoner is a tool call -> tools_condition routes to tools
    # If the latest message (result) from node reasoner is a not a tool call -> tools_condition routes to END
    tools_condition,
)

workflow.add_edge("tools", "reasoner")
#react_graph = workflow.compile()

def ask_bot(query: str, messages: list):
    response = react_graph.invoke({"query": query, "messages": messages})
    return(response)

###################
with st.container():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "compiled_graph" not in st.session_state:
        st.session_state.compiled_graph = workflow.compile()
    
    if "graph_messages" not in st.session_state:
        st.session_state.graph_messages = []


    messages = st.container()#border=True
    
    for message in st.session_state.messages:
        with messages.chat_message(message["role"]):
            st.write(message["content"])

    if query := st.chat_input("Ask your question?"):
        st.session_state.messages.append({"role": "user", "content": query})

        with messages.chat_message("user"):
            st.markdown(query)

        with messages.chat_message("assistant"):
            with st.spinner('Processing...'):
                #out = get_answer(query)
                response = st.session_state.compiled_graph.invoke({"query": query, "messages": st.session_state.graph_messages})
                st.session_state.graph_messages = response['messages']
                out = response['messages'][-1].content
            messages.write(out)
            
        st.session_state.messages.append({"role": "assistant", "content": out})