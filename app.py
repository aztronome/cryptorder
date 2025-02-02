from flask import Flask, render_template, request, jsonify
import ccxt
import logging

app = Flask(__name__)

# Initialize the exchange (Coinbase in this case)
exchange = ccxt.coinbase ({
})

# Set up logging
logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    return render_template(
        'index.html',
        orders=[],  # Default to an empty list
        order_type='buy',  # Default to 'buy'
        coin='BTC'  # Default to 'BTC'
    )

@app.route('/get_price/<coin>', methods=['GET'])
def get_price(coin):
    try:
        # Construct the symbol (e.g., BTC-USDC)
        symbol = f"{coin}-USDC"
        print(symbol)
        # Fetch the ticker for the symbol
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']  # Get the last price
        print(ticker)
        return jsonify({"price": price})

    except Exception as e:
        logging.error(f"Error fetching price for {symbol}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/help')
def help():
    return render_template('help.html')

@app.route('/submit', methods=['POST'])
def submit():
    try:
        # Retrieve input values from the form
        current_price = float(request.form.get('price', 0))
        order_type = request.form.get('order_type', 'buy')  # Get order_type as string
        min_price_amount = float(request.form.get('min_price_amount', 0))
        max_price_amount = float(request.form.get('max_price_amount', 0))
        investment = float(request.form.get('investment', 0))
        scaling_factor = float(request.form.get('scaling_factor', 0))
        num_orders = int(request.form.get('num_orders', 1))
        coin = request.form.get('coin', 'BTC')  # Get the coin symbol from the form
        scale_adjuster = 3.5

        # Determine the symbol (e.g., BTC-USDC)
        symbol = f"{coin}-USDC"

        # Calculate the price range and order width
        price_range = max_price_amount - min_price_amount
        order_width = price_range / (num_orders - 1) if num_orders > 1 else 0

        # Create a normalized weight distribution based on the scaling factor
        weights = [
            (1 + scaling_factor * (num_orders - i - 1) / ((num_orders - 1) * scale_adjuster))
            for i in range(num_orders)
        ]
        if order_type == 'sell':  # Reverse weights for sell orders
            weights = list(reversed(weights))

        # Normalize weights to ensure they sum to 1
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # Calculate orders
        orders = []
        total_investment = 0
        total_quantity = 0

        for i in range(num_orders):
            order_price = round((min_price_amount + (i * order_width)), 2)
            order_amount = round(normalized_weights[i] * investment, 2)
            order_quantity = round(order_amount / order_price, 6)

            total_investment += order_amount
            total_quantity += order_quantity

            orders.append({
                'price': order_price,
                'amount_usd': order_amount,
                'amount_btc': order_quantity
            })

        # Calculate the average cost
        avg_cost = total_investment / total_quantity if total_quantity else 0

        return render_template(
            'index.html',
            orders=orders,
            avg_cost=round(avg_cost, 2),
            total_btc=round(total_quantity, 7),
            order_type=order_type,
            coin=coin
        )

    except Exception as e:
        logging.error(f"Error in /submit: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/cancel_orders', methods=['POST'])
def cancel_orders():
    try:
        data = request.json
        coin = data.get('coin')
        order_type = data.get('order_type', 'buy')  # Get order_type as string

        if not coin:
            logging.error("Missing coin in /cancel_orders request")
            return jsonify({"error": "Missing coin"}), 400

        # Determine the symbol based on the coin
        symbol = f"{coin}-USDC"

        # Fetch all open orders for the symbol
        open_orders = exchange.fetch_open_orders(symbol)

        # Cancel all open orders
        for order in open_orders:
            exchange.cancel_order(order['id'], symbol)

        return jsonify({"success": True, "message": f"All orders for {symbol} canceled"}), 200

    except Exception as e:
        logging.error(f"Error in /cancel_orders: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/place_order', methods=['POST'])
def place_order():
    try:
        orders = request.json.get('orders')
        order_type = request.json.get('order_type', 'buy')  # Get order_type as string
        coin = request.json.get('coin')  # Get coin symbol from the request

        # Determine the symbol based on the coin
        symbol = f"{coin}-USDC"

        for order in orders:
            # Place the order on the exchange
            exchange.create_limit_order(
                symbol=symbol,
                side=order_type,  # Use order_type directly as string
                amount=order['amount_btc'],
                price=order['price']
            )
        return jsonify({"success": True}), 200
    except Exception as e:
        print(f"Error placing order: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)