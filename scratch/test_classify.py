import asyncio
from tradenexus.models import ProductDetails
from tradenexus.core.application import classify_product_role

async def main():
    product = ProductDetails(
        name="solar panels",
        description="solar panels for residential roofing",
        supplier_country="China"
    )
    print("Calling classify_product_role...")
    try:
        role = await classify_product_role(product)
        print("Success! Classified role:")
        print(role.to_dict())
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
