
@"
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings


def get_llm():
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=settings.TEMPERATURE,
        openai_api_key=settings.OPENAI_API_KEY,
    )


def generate_marketing_content(business_type: str, goal: str) -> str:
    llm = get_llm()
    prompt = PromptTemplate(
        input_variables=["business_type", "goal"],
        template="You are an expert marketing strategist.\n\nBusiness Type: {business_type}\nMarketing Goal: {goal}\n\nCreate:\n1. A catchy headline\n2. A short tagline\n3. A 3-sentence elevator pitch\n4. 3 key value propositions\n5. A call-to-action"
    )
    chain = prompt | llm
    result = chain.invoke({"business_type": business_type, "goal": goal})
    return result.content


def generate_business_plan_section(business_type: str, section: str, context: str = "") -> str:
    llm = get_llm()
    messages = [
        SystemMessage(content="You are a seasoned business consultant."),
        HumanMessage(content=f"Business Type: {business_type}\nSection: {section}\nContext: {context}\n\nWrite a comprehensive {section} section.")
    ]
    return llm.invoke(messages).content


def analyze_competitors(business_type: str, market: str) -> str:
    llm = get_llm()
    prompt = PromptTemplate(
        input_variables=["business_type", "market"],
        template="Analyze competition for a {business_type} in {market}. List competitors, weaknesses, gaps, and differentiation strategies."
    )
    chain = prompt | llm
    return chain.invoke({"business_type": business_type, "market": market}).content


def generate_social_media_posts(business_type: str, platform: str, topic: str, count: int = 3) -> list:
    llm = get_llm()
    messages = [
        SystemMessage(content=f"You are a social media expert for {platform}."),
        HumanMessage(content=f"Create {count} {platform} posts for a {business_type} about: {topic}. Number each post.")
    ]
    response = llm.invoke(messages)
    posts = [p.strip() for p in response.content.split('\n\n') if p.strip()]
    return posts if len(posts) >= count else [response.content]
"@ | Set-Content -Path "app\services\ai_service.py" -Encoding UTF8