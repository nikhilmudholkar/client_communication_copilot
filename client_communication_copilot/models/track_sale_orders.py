import datetime

import pandas as pd
from .create_llm_prompt import askai, remove_tags



def track_sale_orders(cursor, order_id):
    # extract sale order ids from the dataframe
    order_id = "'" + order_id + "'"

    print("""SELECT name as sale_order,
                            date_order as ordered_date,
                            commitment_date as due_date,
                            create_uid as created_by
                        FROM sale_order
                        where state = 'sale' and  name = {0}""".format(order_id))

    # get sale_order
    cursor.execute("""SELECT name as sale_order,
                            date_order as ordered_date,
                            commitment_date as due_date,
                            create_uid as created_by
                        FROM sale_order
                        where state = 'sale' and  name = {0}""".format(order_id))
    result = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    df_sale_order = pd.DataFrame(result, columns=columns)

    # strip the time from all the datetime columns. These columns are in string format so convert them to
    # string first convert the datetime columns to strings
    df_sale_order['ordered_date'] = df_sale_order['ordered_date'].astype(str)
    df_sale_order['ordered_date'] = df_sale_order['ordered_date'].str[:10]
    # df_sale_order['ordered_date'] = df_sale_order['ordered_date'].dt.date
    df_sale_order['due_date'] = df_sale_order['due_date'].astype(str)
    df_sale_order['due_date'] = df_sale_order['due_date'].str[:10]
    # print datatype of all the columns
    # print(df_sale_order.dtypes)
    print(df_sale_order)

    # get ordered_products table
    cursor.execute("""SELECT sale_order.name as sale_order,
                        sale_order_line.name as product_name,
                        product_uom_qty as ordered_quantity
                    FROM sale_order
                    inner join sale_order_line
                    ON sale_order.id = sale_order_line.order_id
                    where sale_order.state = 'sale'
                    and sale_order.name = {0}""".format(order_id))
    result = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    df_ordered_products = pd.DataFrame(result, columns=columns)

    # get fulfillment table
    cursor.execute("""SELECT sale_order.name as sale_order,
                        stock_picking.name as delivery_order,
                        stock_picking.state as delivery_state,
                        stock_picking.date_deadline as committed_date,
                        stock_picking.scheduled_date,
                        stock_picking.date_done as delivered_date,
                        stock_picking.priority as delivery_priority
                    FROM sale_order
                    inner join stock_picking
                    ON sale_order.id = stock_picking.sale_id
                    where sale_order.name = {0}""".format(order_id))
    result = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    df_fulfillment = pd.DataFrame(result, columns=columns)

    # strip the time from all the datetime columns
    # convert the datetime columns to strings
    # df_fulfillment['fulfillment_create_date'] = df_fulfillment['fulfillment_create_date'].astype(str)
    # df_fulfillment['fulfillment_create_date'] = df_fulfillment['fulfillment_create_date'].str[:10]
    df_fulfillment['committed_date'] = df_fulfillment['committed_date'].astype(str)
    df_fulfillment['committed_date'] = df_fulfillment['committed_date'].str[:10]
    df_fulfillment['scheduled_date'] = df_fulfillment['scheduled_date'].astype(str)
    df_fulfillment['scheduled_date'] = df_fulfillment['scheduled_date'].str[:10]
    df_fulfillment['delivered_date'] = df_fulfillment['delivered_date'].astype(str)
    df_fulfillment['delivered_date'] = df_fulfillment['delivered_date'].str[:10]
    # print(df_fulfillment.dtypes)

    # get stock_movements table
    cursor.execute("""select sale_order.name as sale_order,
                    table_1.name as delivery_order,
                    table_1.state as delivery_order_state,
                    table_1.create_date as delivery_order_create_date,
                    table_1.product_name,
                    table_1.product_uom_qty as delivery_order_quantity,
                    table_1.reserved_uom_qty as reserved_quantity,
                    table_1.qty_done as delivered_quantity,
                    table_1.write_date as delivery_write_date,
                    table_1.location_id as delivery_origin,
                    table_1.location_dest_id as delivery_destination
                FROM sale_order
                inner join (
                    SELECT sale_id,
                            stock_picking.name,
                            backorder_id,
                            picking_id,
                            table_1a.state,
                            table_1a.product_name,
                            table_1a.stock_movement_id,
                            table_1a.create_date,
                            table_1a.reserved_uom_qty,
                            table_1a.location_id,
                            table_1a.location_dest_id,
                            table_1a.product_uom_qty,
                            table_1a.write_date,
                            table_1a.qty_done
                        FROM stock_picking
                        inner join (
                            SELECT stock_move.picking_id,
                                    stock_move.state,
                                    stock_move.name as product_name, 	
                                    stock_move.create_date,
                                    stock_move.location_id,
                                    stock_move.location_dest_id,
                                    stock_move.id as stock_movement_id,
                                    stock_move_line.reserved_uom_qty,
                                    stock_move.product_uom_qty,
                                    stock_move_line.write_date,
                                    stock_move_line.qty_done
                                FROM stock_move
                                inner join stock_move_line
                                ON stock_move.id = stock_move_line.move_id)
                                AS table_1a
                        ON stock_picking.id = table_1a.picking_id )
                        AS table_1
                ON sale_order.id = table_1.sale_id
                where sale_order.name = {0}""".format(order_id))
    result = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    df_stock_movements = pd.DataFrame(result, columns=columns)

    # strip the time from all the datetime columns
    # convert the datetime columns to strings
    df_stock_movements['delivery_order_create_date'] = df_stock_movements['delivery_order_create_date'].astype(str)
    df_stock_movements['delivery_order_create_date'] = df_stock_movements['delivery_order_create_date'].str[:10]
    df_stock_movements['delivery_write_date'] = df_stock_movements['delivery_write_date'].astype(str)
    df_stock_movements['delivery_write_date'] = df_stock_movements['delivery_write_date'].str[:10]
    # print(df_stock_movements.dtypes)

    # get back_orders table
    cursor.execute("""select sale_order.name as sale_order,
                                table_1.name as backorder_name
                        FROM sale_order
                        inner join (
                        SELECT sale_id,
                        backorder_id,
                        picking_id,
                        stock_picking.name,
                        table_1a.state,
                        table_1a.product_id,
                        table_1a.product_name,
                        table_1a.stock_movement_id,
                        table_1a.create_date,
                        table_1a.reserved_uom_qty,
                        table_1a.location_id,
                        table_1a.location_dest_id,
                        table_1a.product_uom_qty,
                        table_1a.write_date,
                        table_1a.qty_done
                        FROM stock_picking
                        inner join (
                        SELECT stock_move.picking_id,
                        stock_move.state,
                        stock_move.name as product_name,
                        stock_move.product_id, 	
                        stock_move.create_date,
                        stock_move.location_id,
                        stock_move.location_dest_id,
                        stock_move.id as stock_movement_id,
                        stock_move_line.reserved_uom_qty,
                        stock_move.product_uom_qty,
                        stock_move_line.write_date,
                        stock_move_line.qty_done
                        FROM stock_move
                        inner join stock_move_line
                        ON stock_move.id = stock_move_line.move_id)
                        AS table_1a
                        ON stock_picking.id = table_1a.picking_id
                        WHERE stock_picking.backorder_id notnull)
                        AS table_1
                        ON sale_order.id = table_1.sale_id
                        where sale_order.name = {0}""".format(order_id))
    result = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    df_back_orders = pd.DataFrame(result, columns=columns)

    # message = create_llm_message(df_sale_order, df_ordered_products, df_fulfillment, df_stock_movements)

    # url = "http://35.92.128.67:8000/askai"
    # payload for slack webhook endpoint to send messages to a channel
    # payload = {
    #     "question": "Q: Who is elon musk? A: ",
    #     "max_tokens": 100,
    #     "stop": ["Q:", "\n"],
    #     "security_token": "bryo_access_control_1",
    #     # "echo": "true"
    # }

    response_palm = str(order_id) + "\n"
    llm_result = askai(df_sale_order, df_ordered_products, df_fulfillment, df_stock_movements, df_back_orders)
    response_palm = response_palm + llm_result

    return response_palm






