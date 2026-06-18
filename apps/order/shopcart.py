from apps.product.models import Product


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            cart = {}
        self.cart = cart

    def add_with_price(self, product, quantity=1, price=None):
        """اضافه کردن محصول با قیمت مشخص (قیمت تخفیف خورده)"""
        product_id = str(product.id)

        if price is None:
            price = float(product.get_final_price()) if hasattr(product, 'get_final_price') else float(product.price)

        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'price': str(price),
                'title': product.title,
                'slug': product.slug,
                'image': product.image.url if product.image and hasattr(product.image, 'url') else '',
                'code': product.code,
                'brand': product.brand.title if product.brand else 'برند',
            }

        self.cart[product_id]['quantity'] += quantity
        self.save()

    def update_with_price(self, product_id, quantity, price=None):
        """به‌روزرسانی تعداد و قیمت محصول"""
        product_id = str(product_id)
        if product_id in self.cart:
            if quantity <= 0:
                self.remove(product_id)
            else:
                self.cart[product_id]['quantity'] = quantity
                if price:
                    self.cart[product_id]['price'] = str(price)
                self.save()

    def add(self, product, quantity=1):
        """روش قدیمی برای سازگاری"""
        product_id = str(product.id)
        price = float(product.get_final_price()) if hasattr(product, 'get_final_price') else float(product.price)

        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'price': str(price),
                'title': product.title,
                'slug': product.slug,
                'image': product.image.url if product.image and hasattr(product.image, 'url') else '',
                'code': product.code,
                'brand': product.brand.title if product.brand else 'برند',
            }

        self.cart[product_id]['quantity'] += quantity
        self.save()

    def remove(self, product_id):
        product_id = str(product_id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def update(self, product_id, quantity):
        product_id = str(product_id)
        if product_id in self.cart:
            if quantity <= 0:
                self.remove(product_id)
            else:
                self.cart[product_id]['quantity'] = quantity
                self.save()

    def get_total_price(self):
        total = 0
        for item in self.cart.values():
            total += float(item['price']) * item['quantity']
        return total

    def get_total_quantity(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_items_count(self):
        return len(self.cart)

    def get_item(self, product_id):
        product_id = str(product_id)
        return self.cart.get(product_id)

    def clear(self):
        self.cart.clear()
        self.save()

    def save(self):
        self.session['cart'] = self.cart
        self.session.modified = True

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)

        for product in products:
            cart_item = self.cart[str(product.id)]
            yield {
                'product': product,
                'quantity': cart_item['quantity'],
                'price': float(cart_item['price']),
                'total': float(cart_item['price']) * cart_item['quantity']
            }

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())