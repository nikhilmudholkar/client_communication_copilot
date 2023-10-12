import base64
# import json

import pandas as pd

import odoo
from odoo import api, fields, models, _
from .create_llm_prompt import remove_tags, uploadpdftollm, identify_client, identify_sale_orders
from odoo.exceptions import UserError
from .track_sale_orders import track_sale_orders

class Channel(models.Model):
    # added test comment
    _inherit = 'mail.channel'
    print("Inside chilent channel class")
    process_tracker = fields.Char(string="Process Tracker", default="process_started")
    unstructured_data = fields.Char(string="Unstructured Data", default="unstructured_data")
    unstructured_data_formatted = fields.Char(string="Unstructured Data Formatted", default="unstructured_data_formatted")
    ai_message = fields.Char(string="AI Message", default="")
    client_id = fields.Char(string="Client ID", default="client_id")
    # create a variable to store array called order_ids
    order_ids = fields.Char(string="Order IDs", default="order_ids")
    so_filters = fields.Char(string="SO Filters", default="so_filters")

    # this method in all the apps (client_communication_copilot and lead_time_copilot) is called when a message is posted in any channel
    def _notify_thread(self, message, msg_vals=False, json=None, **kwargs):
        print("inside notify message loop for clients with process tracker as ", self.process_tracker)
        # print("message", message)
        if self.process_tracker == 'process_completed':
            self.process_tracker = 'process_started'
        rdata = super(Channel, self)._notify_thread(message, msg_vals=msg_vals, **kwargs)
        # bard_suggestions_channel = self.env.ref('lead_time_copilot.channel_bard_suggestions')
        bryo_channels = self.env['mail.channel'].search([('name', 'ilike', '%Client%')])
        bryo_channel_ids = [channel.id for channel in bryo_channels]
        copilot_user = self.env.ref("client_communication_copilot.copilot_user")
        partner_copilot = self.env.ref("client_communication_copilot.client_copilot_user_partner")
        author_id = msg_vals.get('author_id')
        copilot_name = str(partner_copilot.name or '') + ', '
        res = ""

        if author_id != partner_copilot.id and msg_vals.get('model', '') == 'mail.channel' and msg_vals.get('res_id',
                                                                                                            0) in bryo_channel_ids:
            odoo_bot_user = self.env.ref("base.user_root")
            messages = self.message_ids
            latest_message = remove_tags(messages[0].body)
            latest_author_id = messages[0].author_id.id
            latest_channel_name = messages[0].record_name
            latest_channel = self.env['mail.channel'].search([('name', '=', latest_channel_name)])
            latest_message_attachment = messages[0].attachment_ids
            if latest_message_attachment:
                attachment = latest_channel.message_ids.mapped('attachment_ids')[0]
                # print("Attachment is present")
                pdf_file = base64.decodebytes(attachment.datas)
                # with open(
                #         '/Users/nikhilmukholdar/Personal/fintel_labs/odoo_global/odoo/dev/lead_time_copilot/my_pdf_file_clients.pdf',
                #         'wb') as f:
                #     f.write(pdf_file)
                # response = uploadpdftollm(
                #     '/Users/nikhilmukholdar/Personal/fintel_labs/odoo_global/odoo/dev/lead_time_copilot/my_pdf_file_clients.pdf')

                with open(
                        '/opt/odoo/odoo16/addons/client_communication_copilot/my_pdf_file.pdf',
                        'wb') as f:
                    f.write(pdf_file)
                response = uploadpdftollm(
                    '/opt/odoo/odoo16/addons/client_communication_copilot/my_pdf_file.pdf')


                # latest_channel.with_user(copilot_user).message_post(body=response, message_type='comment',
                #                                                     subtype_xmlid='mail.mt_comment')
                # response = response.replace('\n', ' ')
                # self.unstructured_data = response
                # self.process_tracker = 'identify_vendor'
                latest_message = response
                print(latest_message)
                # convert response to html
                # response = response.replace('\n', '<br/>')
                # response = '<p>' + response + '</p>'
                # latest_channel.with_user(copilot_user).message_post(body=response, message_type='comment',
                #                                                     subtype_xmlid='mail.mt_comment')

                self.unstructured_data = response
                # print("response from mail_channel_clients.py", self.unstructured_data_clients)
                self.process_tracker = 'identify_client'

            if self.process_tracker == 'process_started':
                print("Inside process started")
                print(self.process_tracker)
                self.process_tracker = 'identify_client'
                self.unstructured_data = latest_message
                self.unstructured_data_formatted = messages[0].body
                # replace <br> with \n
                self.unstructured_data_formatted = self.unstructured_data_formatted.replace("<br>", "\n")
                self.unstructured_data_formatted = self.unstructured_data_formatted.replace("<p>", "")
                self.unstructured_data_formatted = self.unstructured_data_formatted.replace("</p>", "")
                print("LATEST MESSAGE: ", self.unstructured_data_formatted)
                self.unstructured_data = self.unstructured_data_formatted
                print(self.unstructured_data)

            if latest_message == "exit":
                print("INSIDE EXIT")
                self.process_tracker = 'process_completed'
                self.unstructured_data = ''
                self.latest_ai_response = ''
                self.vendor_id = ''
                self.product_ids = ''
                self.ai_message = ''
                self.purchase_orders = ''
                self.rfq = False
                print("process completed")

            if self.process_tracker == 'identify_client':
                if latest_message.lower() != "yes" and messages[0].author_id.name not in ['OdooBot', 'Copilot']:
                    self.ai_message = self.ai_message + "\n" + "User: " + latest_message + "\n" + "AI_response: " + res
                    self._cr.execute("""select id as client_id, name as client_name, email, commercial_company_name from res_partner""")
                    result = self._cr.fetchall()
                    columns = [desc[0] for desc in self._cr.description]
                    client_df = pd.DataFrame(result, columns=columns)
                    # print("client_df", client_df)
                    res = identify_client(self.ai_message, client_df)
                    self.latest_ai_response = res
                    import json
                    res_df = pd.DataFrame(json.loads(res), index=[0])
                    res_df = res_df.to_html(index=False)
                    latest_channel.with_user(copilot_user).message_post(body=res_df, message_type='comment',
                                                                        subtype_xmlid='mail.mt_comment')
                    latest_channel.with_user(odoo_bot_user).message_post(
                        body="Is the client identified correctly?Answer yes or no. If no give some context",
                        message_type='comment',
                        subtype_xmlid='mail.mt_comment')
                if latest_message.lower() == "yes":
                    self.process_tracker = 'identify_client_done'
                    self.ai_message = self.unstructured_data
                    if self.latest_ai_response is not None:
                        # print("res is not None")
                        import json
                        res_json = json.loads(self.latest_ai_response)
                    else:
                        res_json = {}
                        print("The res variable is None.")
                # print(res_json)
                    self.client_id = str(res_json['client_id'])
                    latest_channel.with_user(odoo_bot_user).message_post(
                        body="Thank you",
                        message_type='comment',
                        subtype_xmlid='mail.mt_comment')
                    latest_channel.with_user(odoo_bot_user).message_post(
                        body="Is the message regarding a quotation or sale order?Answer with quote or so",
                        message_type='comment',
                        subtype_xmlid='mail.mt_comment')

            if self.process_tracker == 'identify_client_done' and messages[0].author_id.name not in ['OdooBot', 'Copilot']:
                impacted_so = ""
                if latest_message.lower() == "quote":
                    self.so_filters = str(('draft', 'sent'))
                    self.process_tracker = 'quote_or_so_identification_started'
                    # print("rfq identified")
                    latest_channel.with_user(odoo_bot_user).message_post(
                        body="Thank you. Please wait while we fetch your quotes",
                        message_type='comment',
                        subtype_xmlid='mail.mt_comment')
                if latest_message.lower() == "so":
                    self.so_filters = "('" + "sale" + "')"
                    self.process_tracker = 'quote_or_so_identification_started'
                    # print("po identified")
                    latest_channel.with_user(odoo_bot_user).message_post(
                        body="Thank you. Please wait while we fetch your sale orders. If AI responds nothing, ask it to fetch again",
                        message_type='comment',
                        subtype_xmlid='mail.mt_comment')




            if self.process_tracker == 'quote_or_so_identification_started':
                if latest_message.lower != "1" and messages[0].author_id.name not in ['OdooBot', 'Copilot']:
                    self._cr.execute("""select
                                            table_3.sale_order,
                                            table_3.state,
                                            table_3.customer_id,
                                            table_3.customer_name,
                                            table_3.client_order_ref,
                                            table_3.product_name,
                                            table_3.product_id,
                                            table_3.qty_ordered,
                                            table_3.qty_delivered,
                                            table_3.price_unit,
                                            table_3.price_total,
                                            table_3.create_date,
                                            table_3.date_order,
                                            table_3.commitment_date,
                                            table_3.lead_time,
                                            table_3.salesperson,
                                            CONCAT(res_partner.street, ' ', COALESCE(res_partner.street2, ''), ' ', res_partner.zip, ' ', res_partner.city) AS shipping_address
                                        from (
                                            select
                                                table_2.sale_order,
                                                table_2.state,
                                                table_2.customer_id,
                                                table_2.partner_shipping_id,
                                                res_partner.commercial_company_name as customer_name,
                                                table_2.client_order_ref,
                                                table_2.product_name,
                                                table_2.product_id,
                                                table_2.qty_ordered,
                                                table_2.qty_delivered,
                                                table_2.price_unit,
                                                table_2.price_total,
                                                table_2.create_date,
                                                table_2.date_order,
                                                table_2.commitment_date,
                                                table_2.lead_time,
                                                table_2.salesperson
                                            from (
                                                select
                                                  table_1.sale_order,
                                                  table_1.state,
                                                  table_1.customer_id,
                                                  table_1.partner_shipping_id,
                                                  table_1.client_order_ref,
                                                  table_1.product_name,
                                                  table_1.product_id,
                                                  table_1.qty_ordered,
                                                  table_1.qty_delivered,
                                                  table_1.price_unit,
                                                  table_1.price_total,
                                                  table_1.create_date,
                                                  table_1.date_order,
                                                  table_1.commitment_date,
                                                  table_1.lead_time,
                                                  hr_employee.name as salesperson
                                                from (
                                                    SELECT
                                                      sale_order.name as sale_order,
                                                      sale_order.state,
                                                      sale_order.partner_id as customer_id,
                                                      sale_order.partner_shipping_id,
                                                      sale_order.client_order_ref,
                                                      sale_order_line.name as product_name,
                                                      sale_order_line.product_id,
                                                      sale_order_line.product_uom_qty AS qty_ordered,
                                                      sale_order_line.qty_delivered,
                                                      sale_order_line.price_unit,
                                                      sale_order_line.price_total,
                                                      sale_order.create_date,
                                                      sale_order.date_order,
                                                      sale_order.commitment_date,
                                                      sale_order_line.customer_lead as lead_time,
                                                      sale_order_line.salesman_id
                                                    FROM sale_order_line
                                                    LEFT JOIN sale_order
                                                      ON sale_order_line.order_id = sale_order.id
                                                    WHERE sale_order.partner_id = {0} and sale_order.state in {1}
                                                    ) as table_1
                                                left join hr_employee on table_1.salesman_id = hr_employee.user_id) as table_2
                                            left join res_partner on table_2.customer_id = res_partner.id) as table_3
                                        left join res_partner on table_3.partner_shipping_id = res_partner.id""".format(self.client_id, self.so_filters))
                    result = self._cr.fetchall()
                    columns = [desc[0] for desc in self._cr.description]
                    so_df = pd.DataFrame(result, columns=columns)
                    # display all the columns of the so_df
                    print("--------------------------------")
                    pd.set_option('display.max_columns', None)
                    print(so_df)
                    so_df_html = so_df.to_html(index=False)
                    # latest_channel.with_user(copilot_user).message_post(body=so_df_html, message_type='comment',
                    #                                                     subtype_xmlid='mail.mt_comment')

                    res = identify_sale_orders(self.ai_message, so_df)
                    # res = " "
                    self.ai_message = self.ai_message + "\n" + "User: " + latest_message + "\n" + "AI_response: " + impacted_so
                    # remove line breaks from res
                    res = res.replace("\n", "")
                    # check if res is empty
                    if res != "None":
                        self.latest_ai_response = res
                        import json
                        res_json = json.loads(res)
                        res_df = pd.json_normalize(res_json["sale_orders"])
                        # check if res_df is not empty
                        # if not res_df.empty:
                        # select all columns except product_id, price_total, price_total_updated and save the new df as display_df
                        display_df = res_df.drop(columns=['product_id', 'price_total', 'price_total_updated'])

                        display_df_html = display_df.to_html(index=False)
                        display_df_html = display_df_html.replace('<table>', '<table style="font-size: 1px;">')
                        latest_channel.with_user(copilot_user).message_post(body=display_df_html, message_type='comment',
                                                                            subtype_xmlid='mail.mt_comment')
                        latest_channel.with_user(odoo_bot_user).message_post(
                            body="Do you want to track the state of these orders? Reply with 1 if you do",
                            message_type='comment',
                            subtype_xmlid='mail.mt_comment')
                        order_ids = list(set(res_df['sale_order'].tolist()))
                        # convert order_ids to string and store it in self.order_ids
                        # order_ids = ["S00032"]
                        self.order_ids = str(order_ids)
                        self.process_tracker = "sale_orders_identified"

                        # temporary fix because data is not available
                        # order_ids = ["S00056", "S00055"]
                        print("order_ids: ", order_ids)
                        # else:
                        #     latest_channel.with_user(copilot_user).message_post(body="No sale orders identified, trying again",
                        #                                                         message_type='comment',
                        #                                                         subtype_xmlid='mail.mt_comment')



            if self.process_tracker == "sale_orders_identified":
                if latest_message.lower() == "1":
                    self.process_tracker = "sale_orders_tracking"
                    order_ids = self.order_ids
                #     convert order_ids to list
                    order_ids = order_ids.replace("[", "")
                    order_ids = order_ids.replace("]", "")
                    order_ids = order_ids.replace("'", "")
                    order_ids = order_ids.split(",")
                    print("order_ids: ", order_ids)
                    for order_id in order_ids:
                        order_id = order_id.replace(" ", "")
                        sale_order_tracking = track_sale_orders(self._cr, order_id)
                        latest_channel.with_user(copilot_user).message_post(body=sale_order_tracking,
                                                                            message_type='comment',
                                                                            subtype_xmlid='mail.mt_comment')

                # else:
                #     self.process_tracker = "sale_orders_tracking"
                #     latest_channel.with_user(odoo_bot_user).message_post(
                #         body="exit",
                #         message_type='comment',
                #         subtype_xmlid='mail.mt_comment')

        return rdata