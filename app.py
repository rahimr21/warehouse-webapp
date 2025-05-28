import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import event
import csv
from io import StringIO

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///warehouse.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class Box(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    box_number = db.Column(db.String(50), unique=True, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    box_type = db.Column(db.String(20), nullable=False, default='detailed')  # 'detailed' or 'simple'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    contents = relationship('BoxContent', back_populates='box', cascade='all, delete-orphan')
    container_id = db.Column(db.Integer, db.ForeignKey('container.id'), nullable=True)

    def calculate_totals(self):
        totals = {}
        for content in self.contents:
            product_type = content.product_type
            if product_type not in totals:
                totals[product_type] = 0
            totals[product_type] += content.quantity
        return totals
    
    def calculate_lcd_sizes(self):
        lcd_sizes = {}
        for content in self.contents:
            if content.product_type == 'LCDs' and content.lcd_size:
                if content.lcd_size not in lcd_sizes:
                    lcd_sizes[content.lcd_size] = 0
                lcd_sizes[content.lcd_size] += content.quantity
        return lcd_sizes

class BoxContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    box_id = db.Column(db.Integer, db.ForeignKey('box.id'), nullable=False)
    section = db.Column(db.String(20), nullable=False)  # bottom, middle, top
    product_type = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    lcd_size = db.Column(db.String(50), nullable=True)  # For LCD size specification
    box = relationship('Box', back_populates='contents')

class Container(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    boxes = relationship('Box', backref='container', lazy=True)
    custom_boxes = relationship('CustomBox', backref='container', lazy=True)

    def calculate_totals(self):
        totals = {}
        # Count from regular boxes
        for box in self.boxes:
            box_totals = box.calculate_totals()
            for product_type, quantity in box_totals.items():
                if product_type not in totals:
                    totals[product_type] = 0
                totals[product_type] += quantity
        # Count from custom boxes
        for custom_box in self.custom_boxes:
            if custom_box.product_type not in totals:
                totals[custom_box.product_type] = 0
            totals[custom_box.product_type] += custom_box.quantity
        return totals
    
    def calculate_lcd_sizes(self):
        lcd_sizes = {}
        # Count from regular boxes
        for box in self.boxes:
            box_lcd_sizes = box.calculate_lcd_sizes()
            for size, quantity in box_lcd_sizes.items():
                if size not in lcd_sizes:
                    lcd_sizes[size] = 0
                lcd_sizes[size] += quantity
        # Custom boxes don't currently support LCD sizes, but could be added later
        return lcd_sizes

class CustomBox(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(db.Integer, db.ForeignKey('container.id'), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    product_type = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

@app.cli.command('init-db')
def init_db_command():
    """Initialize the database."""
    db.create_all()
    print('Initialized the database.')

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/boxes')
def boxes():
    boxes = Box.query.all()
    return render_template('boxes.html', boxes=boxes)

@app.route('/boxes/new', methods=['GET', 'POST'])
def new_box():
    if request.method == 'POST':
        box_number = request.form.get('box_number')
        weight = float(request.form.get('weight'))
        box_type = request.form.get('box_type', 'detailed')
        container_id = request.form.get('container_id')
        
        # Check if box number already exists
        if Box.query.filter_by(box_number=box_number).first():
            flash('Box number already exists!', 'error')
            return redirect(url_for('new_box'))
        
        box = Box(
            box_number=box_number, 
            weight=weight, 
            box_type=box_type,
            container_id=int(container_id) if container_id else None
        )
        db.session.add(box)
        
        # Process contents based on box type
        if box_type == 'detailed':
            # Process contents for each section
            sections = ['bottom', 'middle', 'top']
            for section in sections:
                products = request.form.getlist(f'{section}_product[]')
                quantities = request.form.getlist(f'{section}_quantity[]')
                lcd_sizes = request.form.getlist(f'{section}_lcd_size[]')
                
                # Process products in pairs (select value, custom input value)
                # Since both select and custom input have same name, they appear consecutively
                i = 0
                while i < len(products) and i // 2 < len(quantities):
                    quantity_index = i // 2
                    quantity = quantities[quantity_index] if quantity_index < len(quantities) else None
                    
                    # Get product name - either from select (even index) or custom input (odd index)
                    product = products[i] if products[i] else (products[i + 1] if i + 1 < len(products) else None)
                    
                    if product and quantity:
                        # Get LCD size - also comes in pairs
                        lcd_size = None
                        if product == 'LCDs' and quantity_index * 2 < len(lcd_sizes):
                            lcd_size = lcd_sizes[quantity_index * 2] if lcd_sizes[quantity_index * 2] else (
                                lcd_sizes[quantity_index * 2 + 1] if quantity_index * 2 + 1 < len(lcd_sizes) else None
                            )
                        
                        content = BoxContent(
                            box=box,
                            section=section,
                            product_type=product,
                            quantity=int(quantity),
                            lcd_size=lcd_size
                        )
                        db.session.add(content)
                    
                    i += 2  # Skip to next pair
        else:  # simple box type
            products = request.form.getlist('simple_product[]')
            quantities = request.form.getlist('simple_quantity[]')
            lcd_sizes = request.form.getlist('simple_lcd_size[]')
            
            # Process products in pairs (select value, custom input value)
            i = 0
            while i < len(products) and i // 2 < len(quantities):
                quantity_index = i // 2
                quantity = quantities[quantity_index] if quantity_index < len(quantities) else None
                
                # Get product name - either from select (even index) or custom input (odd index)
                product = products[i] if products[i] else (products[i + 1] if i + 1 < len(products) else None)
                
                if product and quantity:
                    # Get LCD size - also comes in pairs
                    lcd_size = None
                    if product == 'LCDs' and quantity_index * 2 < len(lcd_sizes):
                        lcd_size = lcd_sizes[quantity_index * 2] if lcd_sizes[quantity_index * 2] else (
                            lcd_sizes[quantity_index * 2 + 1] if quantity_index * 2 + 1 < len(lcd_sizes) else None
                        )
                    
                    content = BoxContent(
                        box=box,
                        section='total',  # Use 'total' for simple boxes
                        product_type=product,
                        quantity=int(quantity),
                        lcd_size=lcd_size
                    )
                    db.session.add(content)
                
                i += 2  # Skip to next pair
        
        db.session.commit()
        flash('Box created successfully!', 'success')
        return redirect(url_for('boxes'))
    
    containers = Container.query.all()
    return render_template('new_box.html', containers=containers)

@app.route('/boxes/<int:box_id>/edit', methods=['GET', 'POST'])
def edit_box(box_id):
    box = Box.query.get_or_404(box_id)
    
    if request.method == 'POST':
        box_number = request.form.get('box_number')
        weight = float(request.form.get('weight'))
        box_type = request.form.get('box_type', 'detailed')
        container_id = request.form.get('container_id')
        
        # Check if box number already exists (excluding current box)
        existing_box = Box.query.filter_by(box_number=box_number).first()
        if existing_box and existing_box.id != box.id:
            flash('Box number already exists!', 'error')
            return redirect(url_for('edit_box', box_id=box_id))
        
        box.box_number = box_number
        box.weight = weight
        box.box_type = box_type
        box.container_id = int(container_id) if container_id else None
        
        # Clear existing contents
        BoxContent.query.filter_by(box_id=box.id).delete()
        
        # Process contents based on box type
        if box_type == 'detailed':
            sections = ['bottom', 'middle', 'top']
            for section in sections:
                products = request.form.getlist(f'{section}_product[]')
                quantities = request.form.getlist(f'{section}_quantity[]')
                lcd_sizes = request.form.getlist(f'{section}_lcd_size[]')
                
                # Process products in pairs (select value, custom input value)
                i = 0
                while i < len(products) and i // 2 < len(quantities):
                    quantity_index = i // 2
                    quantity = quantities[quantity_index] if quantity_index < len(quantities) else None
                    
                    # Get product name - either from select (even index) or custom input (odd index)
                    product = products[i] if products[i] else (products[i + 1] if i + 1 < len(products) else None)
                    
                    if product and quantity:
                        # Get LCD size - also comes in pairs
                        lcd_size = None
                        if product == 'LCDs' and quantity_index * 2 < len(lcd_sizes):
                            lcd_size = lcd_sizes[quantity_index * 2] if lcd_sizes[quantity_index * 2] else (
                                lcd_sizes[quantity_index * 2 + 1] if quantity_index * 2 + 1 < len(lcd_sizes) else None
                            )
                        
                        content = BoxContent(
                            box=box,
                            section=section,
                            product_type=product,
                            quantity=int(quantity),
                            lcd_size=lcd_size
                        )
                        db.session.add(content)
                    
                    i += 2  # Skip to next pair
        else:  # simple box type
            products = request.form.getlist('simple_product[]')
            quantities = request.form.getlist('simple_quantity[]')
            lcd_sizes = request.form.getlist('simple_lcd_size[]')
            
            # Process products in pairs (select value, custom input value)
            i = 0
            while i < len(products) and i // 2 < len(quantities):
                quantity_index = i // 2
                quantity = quantities[quantity_index] if quantity_index < len(quantities) else None
                
                # Get product name - either from select (even index) or custom input (odd index)
                product = products[i] if products[i] else (products[i + 1] if i + 1 < len(products) else None)
                
                if product and quantity:
                    # Get LCD size - also comes in pairs
                    lcd_size = None
                    if product == 'LCDs' and quantity_index * 2 < len(lcd_sizes):
                        lcd_size = lcd_sizes[quantity_index * 2] if lcd_sizes[quantity_index * 2] else (
                            lcd_sizes[quantity_index * 2 + 1] if quantity_index * 2 + 1 < len(lcd_sizes) else None
                        )
                    
                    content = BoxContent(
                        box=box,
                        section='total',
                        product_type=product,
                        quantity=int(quantity),
                        lcd_size=lcd_size
                    )
                    db.session.add(content)
                
                i += 2  # Skip to next pair
        
        db.session.commit()
        flash('Box updated successfully!', 'success')
        return redirect(url_for('boxes'))
    
    containers = Container.query.all()
    return render_template('edit_box.html', box=box, containers=containers)

@app.route('/boxes/<int:box_id>/delete', methods=['POST'])
def delete_box(box_id):
    box = Box.query.get_or_404(box_id)
    db.session.delete(box)
    db.session.commit()
    flash('Box deleted successfully!', 'success')
    return redirect(url_for('boxes'))

@app.route('/containers')
def containers():
    containers = Container.query.all()
    return render_template('containers.html', containers=containers)

@app.route('/containers/new', methods=['GET', 'POST'])
def new_container():
    if request.method == 'POST':
        name = request.form.get('name')
        container = Container(name=name)
        db.session.add(container)
        
        # Process selected boxes
        box_ids = request.form.getlist('box_ids[]')
        for box_id in box_ids:
            box = Box.query.get(box_id)
            if box:
                box.container = container
        
        # Process custom boxes
        custom_products = request.form.getlist('custom_product[]')
        custom_quantities = request.form.getlist('custom_quantity[]')
        custom_weights = request.form.getlist('custom_weight[]')
        
        for product, quantity, weight in zip(custom_products, custom_quantities, custom_weights):
            if product and quantity and weight:
                custom_box = CustomBox(
                    container=container,
                    product_type=product,
                    quantity=int(quantity),
                    weight=float(weight)
                )
                db.session.add(custom_box)
        
        db.session.commit()
        flash('Container created successfully!', 'success')
        return redirect(url_for('containers'))
    
    boxes = Box.query.filter_by(container_id=None).all()
    return render_template('new_container.html', boxes=boxes)

@app.route('/containers/<int:container_id>')
def container_details(container_id):
    container = Container.query.get_or_404(container_id)
    return render_template('container_details.html', container=container)

@app.route('/containers/<int:container_id>/edit', methods=['GET', 'POST'])
def edit_container(container_id):
    container = Container.query.get_or_404(container_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        container.name = name
        
        # Clear existing box assignments
        for box in container.boxes:
            box.container_id = None
        
        # Clear existing custom boxes
        CustomBox.query.filter_by(container_id=container.id).delete()
        
        # Process selected boxes
        box_ids = request.form.getlist('box_ids[]')
        for box_id in box_ids:
            box = Box.query.get(box_id)
            if box:
                box.container = container
        
        # Process custom boxes
        custom_products = request.form.getlist('custom_product[]')
        custom_quantities = request.form.getlist('custom_quantity[]')
        custom_weights = request.form.getlist('custom_weight[]')
        
        for product, quantity, weight in zip(custom_products, custom_quantities, custom_weights):
            if product and quantity and weight:
                custom_box = CustomBox(
                    container=container,
                    product_type=product,
                    quantity=int(quantity),
                    weight=float(weight)
                )
                db.session.add(custom_box)
        
        db.session.commit()
        flash('Container updated successfully!', 'success')
        return redirect(url_for('containers'))
    
    # Get available boxes (not in any container) plus boxes currently in this container
    available_boxes = Box.query.filter(
        (Box.container_id == None) | (Box.container_id == container.id)
    ).all()
    
    return render_template('edit_container.html', container=container, boxes=available_boxes)

@app.route('/containers/<int:container_id>/delete', methods=['POST'])
def delete_container(container_id):
    container = Container.query.get_or_404(container_id)
    
    # Remove container assignment from all boxes
    for box in container.boxes:
        box.container_id = None
    
    # Delete the container (custom boxes will be deleted due to cascade)
    db.session.delete(container)
    db.session.commit()
    flash('Container deleted successfully!', 'success')
    return redirect(url_for('containers'))

@app.route('/containers/<int:container_id>/export')
def export_container(container_id):
    container = Container.query.get_or_404(container_id)
    totals = container.calculate_totals()
    
    # Create CSV content
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Container Report', container.name, container.date.strftime('%Y-%m-%d')])
    writer.writerow([])
    writer.writerow(['Product Type', 'Total Quantity'])
    
    for product_type, quantity in totals.items():
        writer.writerow([product_type, quantity])
    
    output = si.getvalue()
    si.close()
    
    # Create response with CSV content
    from flask import Response
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=container_report_{container.name}_{container.date.strftime("%Y%m%d")}.csv'}
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True) 