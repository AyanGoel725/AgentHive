"""
AgentHive — 📊 Excel Insight Agent
Analyzes DataFrames to find trends, top values, patterns, and generates narrative insights.
"""

from __future__ import annotations
import pandas as pd
from core.config import GOOGLE_API_KEY, MODEL_NAME, is_demo_mode


INSIGHT_PROMPT = """You are a data analyst expert. Analyze the following dataset statistics and provide meaningful insights.

Dataset columns: {columns}
Row count: {row_count}

Statistical summary:
{describe}

Sample data:
{sample}

{query_section}

Provide insights including:
1. Key trends and patterns
2. Notable outliers or anomalies
3. Top values and rankings
4. Correlations between columns
5. Actionable recommendations

Format your response as clear, structured insights:"""


def analyze_dataframe(df: pd.DataFrame, query: str | None = None) -> dict:
    """Analyze a DataFrame and return structured insights."""
    stats = _compute_stats(df)

    if is_demo_mode():
        narrative = _demo_narrative(df, stats, query)
    else:
        narrative = _llm_narrative(df, stats, query)

    return {
        "stats": stats,
        "narrative": narrative,
    }


def _compute_stats(df: pd.DataFrame) -> dict:
    """Compute statistical summaries from the DataFrame."""
    result: dict = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns),
        "dtypes": {col: str(dt) for col, dt in df.dtypes.items()},
    }

    # Numeric column analysis
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        desc = df[numeric_cols].describe().to_dict()
        result["numeric_summary"] = desc

        # Top values per numeric column
        top_values = {}
        for col in numeric_cols:
            top_values[col] = {
                "max": float(df[col].max()) if not pd.isna(df[col].max()) else None,
                "min": float(df[col].min()) if not pd.isna(df[col].min()) else None,
                "mean": float(df[col].mean()) if not pd.isna(df[col].mean()) else None,
                "median": float(df[col].median()) if not pd.isna(df[col].median()) else None,
            }
        result["top_values"] = top_values

        # Correlations
        if len(numeric_cols) > 1:
            corr = df[numeric_cols].corr()
            # Find strong correlations
            strong = []
            for i, c1 in enumerate(numeric_cols):
                for c2 in numeric_cols[i + 1:]:
                    val = corr.loc[c1, c2]
                    if abs(val) > 0.5:
                        strong.append({
                            "col1": c1,
                            "col2": c2,
                            "correlation": round(float(val), 3),
                            "strength": "strong" if abs(val) > 0.7 else "moderate",
                        })
            result["correlations"] = strong

    # Categorical column analysis
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if cat_cols:
        cat_summary = {}
        for col in cat_cols[:5]:
            vc = df[col].value_counts().head(5)
            cat_summary[col] = {
                "unique_count": int(df[col].nunique()),
                "top_values": {str(k): int(v) for k, v in vc.items()},
            }
        result["categorical_summary"] = cat_summary

    # Missing values
    missing = df.isnull().sum()
    missing_cols = {col: int(count) for col, count in missing.items() if count > 0}
    if missing_cols:
        result["missing_values"] = missing_cols

    return result


def _llm_narrative(df: pd.DataFrame, stats: dict, query: str | None = None) -> str:
    """Use LLM to generate narrative insights."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.schema import HumanMessage

    llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.4,
    )

    query_section = f"User query: {query}" if query else ""
    prompt = INSIGHT_PROMPT.format(
        columns=", ".join(df.columns),
        row_count=len(df),
        describe=df.describe().to_string()[:2000],
        sample=df.head(5).to_string()[:1000],
        query_section=query_section,
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


def _demo_narrative(df: pd.DataFrame, stats: dict, query: str | None = None) -> str:
    """Generate insights without LLM for demo mode."""
    lines: list[str] = []
    lines.append("📊 **Excel Dataset Analysis** (Demo Mode)\n")
    lines.append(f"**Dataset:** {stats['row_count']} rows × {stats['column_count']} columns\n")

    # Numeric insights
    top_values = stats.get("top_values", {})
    if top_values:
        lines.append("**📈 Numeric Column Highlights:**")
        for col, vals in list(top_values.items())[:5]:
            lines.append(
                f"  • **{col}**: min={vals['min']}, max={vals['max']}, "
                f"mean={vals['mean']:.2f}, median={vals['median']:.2f}"
                if vals['mean'] is not None else f"  • **{col}**: no numeric data"
            )
        lines.append("")

    # Correlations
    corrs = stats.get("correlations", [])
    if corrs:
        lines.append("**🔗 Notable Correlations:**")
        for c in corrs[:3]:
            direction = "↑ positive" if c["correlation"] > 0 else "↓ negative"
            lines.append(f"  • {c['col1']} ↔ {c['col2']}: {c['correlation']} ({direction}, {c['strength']})")
        lines.append("")

    # Categorical
    cat = stats.get("categorical_summary", {})
    if cat:
        lines.append("**🏷️ Categorical Highlights:**")
        for col, info in list(cat.items())[:3]:
            top = list(info["top_values"].items())[:3]
            top_str = ", ".join(f"{k} ({v})" for k, v in top)
            lines.append(f"  • **{col}**: {info['unique_count']} unique — top: {top_str}")
        lines.append("")

    # Missing
    missing = stats.get("missing_values", {})
    if missing:
        lines.append("**⚠️ Missing Values:**")
        for col, count in missing.items():
            pct = count / stats["row_count"] * 100
            lines.append(f"  • {col}: {count} missing ({pct:.1f}%)")
        lines.append("")

    if query:
        lines.append(f"\n**Query:** \"{query}\" — Full query-driven analysis requires a Gemini API key.")

    return "\n".join(lines)
