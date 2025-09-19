from django.test import TestCase, Client
from django.urls import reverse
from core.models import User, UserProfile, Transaction
from decimal import Decimal
import json
from unittest.mock import patch
import threading
import time

class MpesaConcurrencyTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword', email='test@example.com')
        self.user_profile = UserProfile.objects.create(user=self.user, api_key='test_api_key', balance=Decimal('0.00'))
        self.url = reverse('pagamento_mpesa_api') # Assuming you have a URL named 'pagamento_mpesa_api'

    @patch('portalsdk.APIRequest.execute')
    def test_concurrent_mpesa_payments(self, mock_execute):
        # Mock the M-Pesa API response to always be successful
        mock_execute.return_value = type('obj', (object,), {
            'status_code': 200,
            'body': {
                'output_ResponseCode': 'INS-0',
                'output_TransactionID': 'MPESA_TEST_ID_123',
                'output_ResponseDesc': 'Request processed successfully'
            }
        })

        num_requests = 10
        payment_value = Decimal('100.00')
        expected_balance_increase_per_transaction = payment_value * (Decimal('100.00') - Decimal('10.00')) / Decimal('100.00') # Assuming 10% fee

        # Initial balance
        initial_balance = self.user_profile.balance

        # Prepare data for concurrent requests
        request_data = {
            'numero_celular': '258840000000',
            'valor': str(payment_value)
        }
        headers = {'HTTP_X_API_KEY': 'test_api_key', 'Content-Type': 'application/json'}

        # Function to send a single request
        def send_request():
            response = self.client.post(self.url, data=json.dumps(request_data), **headers)
            return response.status_code, json.loads(response.content)

        # Create and start multiple threads
        threads = []
        results = []
        for _ in range(num_requests):
            thread = threading.Thread(target=lambda: results.append(send_request()))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Assertions
        self.assertEqual(len(results), num_requests)

        successful_transactions = 0
        for status_code, response_content in results:
            self.assertEqual(status_code, 200)
            self.assertEqual(response_content['status'], 'success')
            self.assertIn('transaction_id', response_content)
            self.assertIn('external_transaction_id', response_content)
            self.assertIn('internal_transaction_id', response_content)
            successful_transactions += 1
        
        self.assertEqual(successful_transactions, num_requests)

        # Verify the final balance
        self.user_profile.refresh_from_db()
        expected_final_balance = initial_balance + (expected_balance_increase_per_transaction * num_requests)
        self.assertEqual(self.user_profile.balance, expected_final_balance)

        # Verify the number of transactions created
        self.assertEqual(Transaction.objects.count(), num_requests)

        # Verify that all created transactions have unique internal and external IDs
        internal_ids = [t.id for t in Transaction.objects.all()]
        external_ids = [t.external_transaction_id for t in Transaction.objects.all()]
        
        self.assertEqual(len(set(internal_ids)), num_requests)
        # Note: external_ids might not be unique if M-Pesa API returns the same ID for all mocked successful transactions
        # However, if the mock is set to return a unique ID, then this should pass.
        # For this test, we are mocking a single external_transaction_id, so this assertion needs to be adjusted
        # if the mock is not designed to return unique external IDs.
        # For now, we'll assert that all external IDs are the same as the mocked one.
        for ext_id in external_ids:
            self.assertEqual(ext_id, 'MPESA_TEST_ID_123')
        
        # If you want to test unique external IDs, you would need a more sophisticated mock
        # mock_execute.side_effect = [
        #     type('obj', (object,), {'status_code': 200, 'body': {'output_ResponseCode': 'INS-0', 'output_TransactionID': f'MPESA_TEST_ID_{i}', 'output_ResponseDesc': 'Success'}})
        #     for i in range(num_requests)
        # ]
        # self.assertEqual(len(set(external_ids)), num_requests)
