import random
from app import model,payment_pb2



def random_boolean():
    return random.random() < 0.9

async def create_payment(payment_request: model.PaymentRequest):
    result = random_boolean()
    if result:
        return payment_pb2.PaymentStatus.PAID
    else:
         return payment_pb2.PaymentStatus.FAILED
        

