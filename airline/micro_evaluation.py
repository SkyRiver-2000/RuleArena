import os
import json
import numpy as np
import pandas as pd
import openai

from structure import Response, rule_list, error_analysis

system_prompt = "You are a helpful assistant at American Airlines and an expert at structured data extraction. You are given the information of a passenger, his / her items, his / her special needs, the policies of American Airlines, and a textual analysis calculating the total cost (including the flight ticket fee, checked bag fees, cost of special needs). You should convert the unstructured textual analysis into the given structure."

prompt_template = """
The policies of American Airlines are as follows:

# Bag fees
All published bag fees apply at each check-in location and are base rates according to travel dates and destination; applicable taxes are not shown.

## Carry-on bags
You're allowed 1 carry-on bag and 1 personal item in all cabins.

### Personal items
Your personal item like a purse or small handbag must fit under the seat in front of you. Dimensions should not exceed 18 x 14 x 8 inches (45 x 35 x 20 cm).

These don't count as your personal item or carry-on:
* Diaper bags (1 per child)
* Breast pump
* Small, soft-sided cooler of breast milk
* Child safety seats, strollers and medical or mobility devices

### Carry-on items
You can bring only one carry-on item along with your personal item. Your carry-on must fit in in the overhead bin or under the seat in front of you. If it doesn't fit, it will need to be checked. Be sure all your carry-on items are labeled in case they are checked.

#### Carry-on bag
The total size of your carry-on, including the handles and wheels, cannot exceed 22 x 14 x 9 inches (56 x 36 x 23 cm) and must fit in the sizer at the airport.

#### Soft-sided garment bag
Your soft-sided garment bag cannot exceed 51 inches / 130 cm (length + width + height).

## Checked bags
Bag fees have been updated effective for tickets issued on / after February 20, 2024.

Travel within / between the U.S., Puerto Rico, and U.S. Virgin Islands – 1st checked bag fee is $40 and the 2nd checked bag fee is $45.

Travel to / from Canada, Caribbean, Mexico, Central America, and Guyana – 1st checked bag fee is $35 and the 2nd checked bag fee is $45.

All bag fees are non-refundable and apply per person, each way, even if you buy or get an upgrade that includes free checked bags. If you believe you were incorrectly charged for bag fees, contact an American representative for help or file a refund claim within 45 days.

### First Bag

| Regions                                                                                                                                                                              | Basic Economy | Main Cabin^ | Premium Economy | Business | First |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|-------------|-----------------|----------|-------|
| Within and between U.S., Puerto Rico and U.S. Virgin Islands                                                                                                                         | $40           | $40         | $0              | $0       | $0    |
| Within and between Canada and U.S., Puerto Rico and U.S. Virgin Islands                                                                                                              | $35           | $35         | $0              | $0       | $0    |
| Between Mexico, Caribbean (excluding Cuba/Haiti), Central America (excluding Panama) and U.S., Puerto Rico, U.S. Virgin Islands, Canada                                              | $35           | $35         | —               | $0       | $0    |
| From U.S., Puerto Rico, U.S. Virgin Islands, Canada, Mexico and the Caribbean (excluding Haiti) to Cuba                                                                              | $35           | $0          | —               | $0       | $0    |
| From Cuba to U.S., Puerto Rico, U.S. Virgin Islands, Canada, Mexico and the Caribbean (including Haiti)                                                                              | $0            | $0          | $0              | $0       | $0    |
| To or from Haiti                                                                                                                                                                     | $35           | $0          | —               | $0       | $0    |
| Between Guyana, Suriname and U.S., Puerto Rico, U.S. Virgin Islands, Canada, Mexico, Caribbean (excluding Haiti and Cuba), Central America (excluding Panama)                        | $35           | $35         | $0              | $0       | $0    |
| Between Panama, Colombia, Ecuador, Peru and U.S., Puerto Rico, U.S. Virgin Islands, Canada, Mexico, Caribbean, Central America                                                       | $45           | $0          | $0              | $0       | $0    |
| Between South America (excluding Colombia, Ecuador, Peru, Guyana, Suriname) and U.S., Puerto Rico, U.S. Virgin Islands, Canada, Mexico, Caribbean (including Haiti), Central America | $60           | $0          | $0              | $0       | $0    |
| Between Israel and U.S., Puerto Rico, U.S. Virgin Islands, Canada, Mexico, Caribbean (including Haiti), Central America, South America                                               | $75           | $0          | $0              | $0       | $0    |
| Between Qatar and U.S., Puerto Rico, U.S. Virgin Islands, Canada, Mexico, Caribbean (including Haiti), Central America, South America                                                | $75           | $0          | $0              | $0       | $0    |
| Between Europe and U.S., Puerto Rico or connecting via Europe to another destination                                                                                                 | $75           | $0          | $0              | $0       | $0    |
| To or from India, China, Japan, South Korea, Hong Kong, Australia and New Zealand                                                                                                    | $75           | $0          | $0              | $0       | $0    |

^Main Plus includes 1 extra free checked bag in addition to the Main Cabin allowance (max of 2).

### Second Bag

| Regions                                                                                                                                                                     | Basic Economy | Main Cabin^ | Premium Economy | Business | First |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|-------------|-----------------|----------|-------|
| Within and between U.S., Canada, Puerto Rico and U.S. Virgin Islands                                                                                                        | $45           | $45         | $0              | $0       | $0    |
| Between Honduras and U.S., Puerto Rico, U.S. Virgin Islands, Canada, Mexico, Caribbean (excluding Cuba/Haiti), Central America (excluding Panama)                           | $45           | $45         | —               | $0       | $0    |
| Between Mexico, Caribbean (excluding Cuba/Haiti) or Central America (excluding Panama and Honduras) and U.S., Puerto Rico, U.S. Virgin Islands, Canada                      | $45           | $45         | —               | $0       | $0    |
| Between Haiti and U.S., Puerto Rico, U.S. Virgin Islands, Canada, Mexico, Caribbean (excluding Cuba), Central America (excluding Panama)                                    | $65           | $65         | —               | $0       | $0    |
| From all regions to Cuba                                                                                                                                                    | $150          | $150        | —               | $0       | $0    |
| From Cuba to all regions                                                                                                                                                    | $0            | $0          | —               | $0       | $0    |
| Between Panama and U.S., Puerto Rico, U.S. Virgin Islands, Canada, Mexico, Caribbean (excluding Cuba), Central America                                                      | $100          | $100        | $0              | $0       | $0    |
| Between Guyana, Suriname and U.S., Puerto Rico, U.S. Virgin Islands, Canada, Mexico, Caribbean (excluding Haiti and Cuba), Central America (excluding Panama)               | $45           | $45         | —               | $0       | $0    |
| Between South America (excluding Guyana, Suriname) and U.S., Puerto Rico, U.S. Virgin Islands, Canada, Mexico, Caribbean (including Haiti, excluding Cuba), Central America | $100          | $100        | $0              | $0       | $0    |
| Between Europe, Israel, Qatar and U.S., Puerto Rico, U.S. Virgin Islands, Canada, Mexico, Caribbean (excluding Cuba), Central America, South America                        | $100          | $100        | $0              | $0       | $0    |
| To or from India, China, Japan, South Korea, Hong Kong, Australia and New Zealand                                                                                           | $100          | $100        | $0              | $0       | $0    |

^Main Plus includes 1 extra free checked bag in addition to the Main Cabin allowance (max of 2).

### Third Bag

| Regions                                                                                                                                                    | Basic Economy | Main Cabin | Premium Economy | Business | First  |
|------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|------------|-----------------|----------|--------|
| Within and between U.S., Canada, Puerto Rico and U.S. Virgin Islands                                                                                       | $150          | $150       | $150            | $150     | $150   |
| Between Mexico, Caribbean, Central America, South America and U.S., Puerto Rico, U.S. Virgin Islands, Canada; or Between the Caribbean and Central America | $200          | $200       | $200            | $200     | $0     |
| Between Europe, Israel, Qatar and U.S., Puerto Rico, U.S. Virgin Islands, Canada, Mexico, Caribbean, Central America, South America                        | $200          | $200       | $200            | $200     | $0     |
| To or from India, China, Japan, South Korea, Hong Kong, Australia and New Zealand                                                                          | $200          | $200       | $200            | $200     | $0     |

### Fourth Bag +

| Regions                                                                                                                                                                        | Basic Economy | Main Cabin | Premium Economy | Business | First  |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|------------|-----------------|----------|--------|
| Within and between U.S., Canada, Puerto Rico and U.S. Virgin Islands                                                                                                           | $200          | $200       | $200            | $200     | $200   |
| Between Mexico, Caribbean or Central America, South America and U.S., Puerto Rico, U.S. Virgin Islands, Canada or between Mexico, Caribbean and Central America, South America | $200          | $200       | $200            | $200     | $200   |
| Between Europe, Israel, Qatar and U.S., Puerto Rico, U.S. Virgin Islands, Canada, Mexico, Caribbean, Central America and South America                                         | $200          | $200       | $200            | $200     | $200   |
| To or from India, China, Japan, South Korea, Hong Kong, Australia and New Zealand                                                                                              | $200          | $200       | $200            | $200     | $200   |

### Complimentary Bags

In some cases, you won't have to pay the fees for up to 3 bags when traveling on itineraries marketed and operated by American Airlines. If you qualify for complimentary bags based on your AAdvantage® status or oneworld® status, the benefits are based on your highest status level at time of ticketing or check-in.

If your status level is:
* Higher at ticketing than at check-in, show your ticket receipt to the airport agent
* Lower at ticketing than at check-in, current benefits will automatically apply

Free checked bags may not apply to codeshare flights operated by our partners. Visit the website of the airline operating your flight for details.

1st checked bag is complimentary for:
* Eligible AAdvantage® Aviator® and Citi® / AAdvantage® cardmembers (on domestic American Airlines operated itineraries)
* AAdvantage Gold® status
* GOL Diamond Smiles members
* oneworld® Ruby

or when traveling to these destinations (excluding Basic Economy):
* Argentina
* Australia
* Brazil
* Chile
* China
* Colombia
* Cuba
* Ecuador
* El Salvador
* Haiti
* Hong Kong
* India
* Israel
* Japan
* New Zealand
* Panama
* Paraguay
* Peru
* Qatar
* South Korea
* Transatlantic
* Uruguay

1st and 2nd checked bags are complimentary for:
* AAdvantage Platinum® status
* oneworld® Sapphire members
* Confirmed Domestic First customers
* Confirmed Business customers
* Confirmed Premium Economy customers

1st, 2nd and 3rd checked bags are complimentary for:
* Confirmed Flagship® First and Flagship® Business Plus customers
* AAdvantage Executive Platinum® status
* AAdvantage Platinum Pro® status
* oneworld® Emerald
* Active U.S. military and / or dependents with ID traveling on orders (1st - 5th bags free of charge)
* Active U.S. military with ID on personal travel

### Weight and Size
We calculate the size limits of your bag by adding the total outside dimensions of each bag, length + width + height.

For all regions, except to / from Australia or New Zealand, your checked bag allowance is:
* Dimension: 62 in / 158 cm
* Weight: 50 lbs / 23 kgs
* For First / Business, weight is 70 lbs / 32 kgs for complimentary bags and 50 lbs / 23 kgs for excess charged bags

For all confirmed customers on flights to / from Australia or New Zealand:
* Dimension: 62 in / 158 cm
* Weight: 70 lbs / 32kgs for complimentary bags and 50 lbs / 23 kgs for excess charged bags

#### Overweight Bags

More than one fee may apply per bag that exceeds standard dimensions for both weight and size. The higher fee between oversize and overweight applies, in addition to the checked bag fee.

##### Over 50 lbs / 23 kgs to 53 lbs / 24 kgs

| Regions     | Basic Economy | Main Cabin | Premium Economy | Business | First  |
|-------------|---------------|------------|-----------------|----------|--------|
| All Regions | $30           | $30        | $30             | $30      | $30    |

##### Over 53 lbs / 24 kgs to 70 lbs / 32 kgs

| Regions                                                                                                                                                      | Basic Economy | Main Cabin | Premium Economy | Business   | First     |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|------------|-----------------|------------|-----------|
| Within and between U.S., Canada, Puerto Rico and U.S. Virgin Islands                                                                                         | $100          | $100       | $100            | $100       | $100      |
| To / From Cuba                                                                                                                                               | $200          | $200       | $200            | $200       | $200      |
| Between Mexico, Caribbean or Central America, South America and U.S., Puerto Rico, U.S. Virgin Islands, Canada; or between the Caribbean and Central America | $100          | $100       | $100            | $100       | $100      |
| Between Europe, Israel, Qatar and U.S., Puerto Rico, U.S. Virgin Islands, Canada, Mexico, Caribbean, Central America, South America                          | $100          | $100       | $100            | $100       | $100      |
| To or from Australia and New Zealand                                                                                                                         | $100          | $100       | $100            | $100       | $100      |
| To or from India, China, Japan, South Korea and Hong Kong                                                                                                    | $100          | $100       | $100            | $100       | $100      |

##### Over 70 lbs / 32kgs to 100 lbs / 45 kgs

| Regions                                                                                                                                                    | Basic Economy | Main Cabin    | Premium Economy | Business       | First          |
|------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|---------------|-----------------|----------------|----------------|
| Within and between U.S., Canada, Puerto Rico and U.S. Virgin Islands                                                                                       | $200          | $200          | $200            | $200           | $200           |
| Between Mexico, Caribbean, Central America, South America and U.S., Puerto Rico, U.S. Virgin Islands, Canada; or between the Caribbean and Central America | $200          | $200          | $200            | $200           | $200           |
| Between Europe, Israel, Qatar and U.S., Puerto Rico, U.S. Virgin Islands, Canada, Mexico, Caribbean, Central America, South America                        | Not accepted  | Not accepted  | Not accepted    | Not accepted   | Not accepted   |
| To or from Australia and New Zealand                                                                                                                       | Not accepted  | Not accepted  | Not accepted    | Not accepted   | Not accepted   |
| To or from India, China, Japan, South Korea and Hong Kong                                                                                                  | $450          | $450          | $450            | $450           | $450           |

#### Oversize Bags

| Region                                                                       | Over 62 in / 158 cm – 65 in / 165 cm | Over 65 in / 165 cm – 115 in / 292 cm |
|------------------------------------------------------------------------------|--------------------------------------|---------------------------------------|
| Between U.S., Puerto Rico, U.S. Virgin Islands and Canada                    | $30                                  | $200                                  |
| Mexico / Caribbean / Central America (except Panama) / Guyana / Suriname     | $30                                  | $200                                  |
| Panama / South America (except Guyana / Suriname)                            | $30                                  | $150                                  |
| Europe, Israel, Qatar                                                        | $30                                  | $150                                  |
| China, Japan, South Korea, Hong Kong, India, Australia, and New Zealand      | $30                                  | $200                                  |

$question_prompt Compute the total cost for him step by step and end your response with "The total cost is $xxx." (xxx is a number)
Analysis:
$response

Do NOT include the carry-on item into your list of `checked_bags`.
You should organize the order of items in your list of `checked_bags` according to item ID.
"""
    
def gpt(inputs):
    api_key = os.environ["OPENAI_API_KEY"]
    engine = openai.OpenAI(api_key=api_key)
    response = engine.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": inputs}
        ],
        response_format=Response,
        temperature=0.0,
    )
    return response.choices[0].message.parsed

def load_problems(bag_num: int, complexity: int):
    with open(f"synthesized_problems/bag_num_{bag_num}_complexity_{complexity}.jsonl", "r") as f:
        problems = [json.loads(l) for l in f]
    return problems
    
def check_rule_application(question_prompt: str, info_dict: dict, response: str):
    prompt = prompt_template.replace("$question_prompt", question_prompt)
    prompt = prompt.replace("$response", response)
    
    parsing_response = gpt(prompt)
    return error_analysis(parsing_response, info_dict), parsing_response

def compute_metrics(rule_app_checklist: list[str]):
    rule_wise = {r: [] for r in rule_list}
    correct, missing, error = 0, 0, 0
    for tag in rule_app_checklist:
        tag_type = tag[:tag.find(": ")]
        tag_rule = tag[tag.find(": ")+2:]
        if tag_rule in rule_wise:
            rule_wise[tag_rule].append(tag_type)
            if tag_type == "Missing":
                missing += 1
            elif tag_type == "Error":
                error += 1
            else:
                correct += 1
    problem_wise_metrics = {
        "precision": correct / (correct + error),
        "recall": correct / (correct + missing),
    }
    return problem_wise_metrics, rule_wise

def aggregate_rule_wise_metrics(rule_wise_app_list: dict[str, list[str]]):
    rule_wise_recall, rule_wise_precision, rule_wise_total = \
        {r: np.nan for r in rule_list}, {r: np.nan for r in rule_list}, {r: 0 for r in rule_list}
    for rule, app_list in rule_wise_app_list.items():
        if len(app_list) == 0:
            continue
        value_cnt = pd.value_counts(app_list)
        rule_wise_recall[rule] = (len(app_list) - value_cnt.get("Missing", 0)) / len(app_list)
        if value_cnt.get("Correct", 0) + value_cnt.get("Error", 0) > 0:
            rule_wise_precision[rule] = value_cnt.get("Correct", 0) / (value_cnt.get("Correct", 0) + value_cnt.get("Error", 0))
        else:
            rule_wise_precision[rule] = np.nan # NOTE: fail to recall
        rule_wise_total[rule] = len(app_list)
    return rule_wise_recall, rule_wise_precision, rule_wise_total