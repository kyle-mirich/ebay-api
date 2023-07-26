import streamlit as st
import os
from ebaysdk.finding import Connection as Finding
from ebaysdk.exception import ConnectionError
from datetime import datetime, timedelta

EBAY_APP_ID = os.getenv('EBAY_APP_ID')  # replace with your own eBay API key

if EBAY_APP_ID is None:
    raise ValueError("EBAY_APP_ID environment variable not set")

CONDITIONS = {
    'None': (None, None),
    'New': ('New', '1000'),
    'Used': ('Used', '3000'),
    'For parts': ('For parts', '7000')
}

SORT_ORDERS = {
    'Best Match': 'BestMatch',
    'Price + Shipping Lowest': 'PricePlusShippingLowest',
    'Price + Shipping Highest': 'PricePlusShippingHighest',
    'Newly Listed': 'StartTimeNewest',
    'Ending Soonest': 'EndTimeSoonest'
}

api_call_counter = 0
MAX_API_CALL = 5

def get_active_listings(item_name, condition_name, sort_order_name):
    global api_call_counter

    condition_id = CONDITIONS[condition_name][1]
    condition_text = CONDITIONS[condition_name][0]
    sort_order = SORT_ORDERS[sort_order_name]

    api = Finding(appid=EBAY_APP_ID, config_file=None, siteid="EBAY-US", domain="svcs.ebay.com")

    try:
        prices = []
        items = []
        
        if api_call_counter >= MAX_API_CALL:
            return items, prices

        request = {
            'keywords': item_name,
            'paginationInput': {
                'entriesPerPage': 100,
                'pageNumber': 1
            },
            'sortOrder': sort_order
        }
        if condition_id is not None:
            request['itemFilter'] = [{'name': 'Condition', 'value': condition_id}]

        response = api.execute('findItemsByKeywords', request)
        api_call_counter += 1

        if response.reply.ack == 'Success':
            searchResult = response.dict()['searchResult']
            if 'item' in searchResult:
                items += searchResult['item']
                prices += [(float(item['sellingStatus']['currentPrice']['value']), item['viewItemURL']) for item in searchResult['item']]

        return items, prices

    except ConnectionError as e:
        st.error('Failed to connect to eBay API: {}'.format(e))
    except KeyError as e:
        st.error('KeyError: {}'.format(e))

def get_average_sold_price(item_name, condition_name):
    global api_call_counter

    condition_id = CONDITIONS[condition_name][1]
    condition_text = CONDITIONS[condition_name][0]

    api = Finding(appid=EBAY_APP_ID, config_file=None, siteid="EBAY-US", domain="svcs.ebay.com")

    try:
        prices = []
        items = []
        
        if api_call_counter >= MAX_API_CALL:
            return items, prices

        now = datetime.now()
        one_year_ago = now - timedelta(days=365)

        now_str = now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        one_year_ago_str = one_year_ago.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        request = {
            'keywords': item_name,
            'paginationInput': {
                'entriesPerPage': '100',
                'pageNumber': '1'
            },
            'sortOrder': 'EndTimeSoonest',
            'itemFilter': [
                {'name': 'SoldItemsOnly', 'value': 'true'},
                {'name': 'EndTimeFrom', 'value': one_year_ago_str},
                {'name': 'EndTimeTo', 'value': now_str}
            ]
        }
        if condition_id is not None:
            request['itemFilter'].append({'name': 'Condition', 'value': condition_id})

        response = api.execute('findCompletedItems', request)
        api_call_counter += 1

        if response.reply.ack == 'Success':
            searchResult = response.dict()['searchResult']
            if 'item' in searchResult:
                items += searchResult['item']
                prices += [(float(item['sellingStatus']['currentPrice']['value']), item['viewItemURL']) for item in searchResult['item']]

        return items, prices

    except ConnectionError as e:
        st.error('Failed to connect to eBay API: {}'.format(e))
    except KeyError as e:
        st.error('KeyError: {}'.format(e))

def main():
    st.title('Ebay Listings Analyzer')

    item_name = st.text_input("What item would you like to analyze?")
    condition_name = st.selectbox("What condition should the item be in?", list(CONDITIONS.keys()))
    sort_order_name = st.selectbox("How would you like to sort the results?", list(SORT_ORDERS.keys()))
    listings_type = st.selectbox("Which type of listings would you like to analyze?", ["Active", "Completed", "Both"])

    if st.button('Analyze'):
        if listings_type in ["Active", "Both"] and api_call_counter < MAX_API_CALL:
            items, prices = get_active_listings(item_name, condition_name, sort_order_name)
            if prices:
                average_price = sum(price for price, _ in prices) / len(prices)
                low_price, low_price_link = min(prices, default=(0, None))
                high_price, high_price_link = max(prices, default=(0, None))
                most_recent_listing = max(items, key=lambda item: item['listingInfo']['startTime'])
                most_recent_listing_link = most_recent_listing['viewItemURL']
                most_recent_listing_price = float(most_recent_listing['sellingStatus']['currentPrice']['value'])
                st.write(f"Active listings for {item_name} in {condition_name} condition:")
                st.write(f"Average price: ${average_price:.2f}")
                st.write(f"Low price: [${low_price:.2f}]({low_price_link})")
                st.write(f"High price: [${high_price:.2f}]({high_price_link})")
                st.write(f"Most recent listing price: [${most_recent_listing_price:.2f}]({most_recent_listing_link})")

        if api_call_counter < MAX_API_CALL and listings_type in ["Completed", "Both"]:
            items, prices = get_average_sold_price(item_name, condition_name)
            if prices:
                average_price = sum(price for price, _ in prices) / len(prices)
                low_price, low_price_link = min(prices, default=(0, None))
                high_price, high_price_link = max(prices, default=(0, None))
                most_recent_listing = max(items, key=lambda item: item['listingInfo']['endTime'])
                most_recent_listing_link = most_recent_listing['viewItemURL']
                most_recent_listing_price = float(most_recent_listing['sellingStatus']['currentPrice']['value'])
                st.write(f"Completed listings for {item_name} in {condition_name} condition:")
                st.write(f"Average sold price: ${average_price:.2f}")
                st.write(f"Lowest price sold: [${low_price:.2f}]({low_price_link})")
                st.write(f"Highest price sold: [${high_price:.2f}]({high_price_link})")
                st.write(f"Most recent sold price: [${most_recent_listing_price:.2f}]({most_recent_listing_link})")

        if api_call_counter >= MAX_API_CALL:
            st.write("Maximum API call limit reached. Please try again later.")


if __name__ == "__main__":
    main()
