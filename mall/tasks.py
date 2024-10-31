from celery import shared_task

@shared_task
def cancel_payment(payment_id, reason):
    from mall.models import OrderPayment  # 함수 내부에서 임포트

    payment = OrderPayment.objects.get(id=payment_id)
    try:
        payment.cancel(reason)
        return {"status": "success", "message": "Payment cancelled successfully."}
    except Exception as e:
        return {"status": "failed", "message": str(e)}
