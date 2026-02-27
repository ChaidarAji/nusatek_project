from odoo import models, fields, api, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    project = fields.Char(string="Project")
    package = fields.Char(string="Package ID")


    def _get_7energi_do_lines(self):
        """
        Build print lines for QWeb using stock.move (move_ids_without_package).

        Output:
        - {'type':'main', ...} => numbered by QWeb
        - {'type':'sub',  ...} => dash line, not numbered

        Rules:
        - Component move = kit_component=True AND sale_line_id exists
        - Normal sale move = sale_line_id exists AND kit_component=False
        - Material Tambahan = sale_line_id is False (includes orphan kit_component)
        - BOM source for kit qty = move.bom_id (from component moves)
        """
        self.ensure_one()

        # -------------------------
        # Helpers
        # -------------------------
        def fmt_qty(qty):
            if qty is None or qty == "":
                return 0
            try:
                q = float(qty)
                if q <= 0:
                    return 0
                s = ("%s" % q)
                if "." in s:
                    s = s.rstrip("0").rstrip(".")
                return s
            except Exception:
                return str(qty)

        def is_kit_component(m):
            # Prefer stock.move.kit_component
            if hasattr(m, "kit_component"):
                return bool(getattr(m, "kit_component"))

            # Fallback to stock.move.line.kit_component
            mls = getattr(m, "move_line_ids", self.env["stock.move.line"])
            if mls and hasattr(mls[:1], "kit_component"):
                return any(bool(ml.kit_component) for ml in mls)
            return False

        def move_qty(m):
            # Your current rule: only done qty
            return m.quantity_done or 0.0

        def to_uom(qty, from_uom, to_uom):
            try:
                return from_uom._compute_quantity(qty, to_uom)
            except Exception:
                return qty

        def move_desc(m, fallback=""):
            """Prefer description_picking; fallback if empty."""
            dp = (getattr(m, "description_picking", False) or "").strip()
            return dp or (fallback or "")

        def add_main(desc, code="", qty="", uom="", note="", is_section_header=False):
            lines.append({
                "type": "main",
                "description": desc or "",
                "code": code or "",
                "qty": fmt_qty(qty) if qty != "" else 0,
                "uom": uom or "",
                "note": note or "",
                "is_section_header": bool(is_section_header),
            })

        def add_sub(desc, code="", qty="", uom="", note=""):
            lines.append({
                "type": "sub",
                "description": desc or "",
                "code": code or "",
                "qty": fmt_qty(qty) if qty != "" else 0,
                "uom": uom or "",
                "note": note or "",
            })

        def sum_moves_by_product(moves, target_uom_getter=None):
            """
            Group moves by product and sum quantities.
            Additionally keep:
            - 'move': representative move (first seen)
            - 'desc': first non-empty description_picking found for that product
            """
            out = {}
            for m in moves:
                qty = move_qty(m)
                # if qty <= 0:
                #     continue

                p = m.product_id
                from_uom = m.product_uom or p.uom_id
                to_uom_rec = (target_uom_getter(p) if target_uom_getter else p.uom_id)
                qty_conv = to_uom(qty, from_uom, to_uom_rec)

                if p.id not in out:
                    out[p.id] = {
                        "product": p,
                        "qty": 0.0,
                        "uom": to_uom_rec,
                        "move": m,
                        "desc": "",   # first non-empty description_picking
                    }

                out[p.id]["qty"] += qty_conv

                # capture first non-empty description_picking for the grouped product
                if not out[p.id]["desc"]:
                    dp = (getattr(m, "description_picking", False) or "").strip()
                    if dp:
                        out[p.id]["desc"] = dp

            return out

        def compute_kit_qty_from_bom(comp_moves, sale_uom):
            bom = False
            for m in comp_moves:
                if hasattr(m, "bom_id") and m.bom_id:
                    bom = m.bom_id
                    break
            if not bom or not getattr(bom, "bom_line_ids", False):
                return ""

            bom_uom = getattr(bom, "product_uom_id", False)
            bom_uom = bom_uom or (bom.product_tmpl_id.uom_id if getattr(bom, "product_tmpl_id", False) else sale_uom)

            got_map = {}
            for m in comp_moves:
                p = m.product_id
                qty = move_qty(m)
                # if qty <= 0:
                #     continue
                from_uom = m.product_uom or p.uom_id
                qty_in_puom = to_uom(qty, from_uom, p.uom_id)
                got_map[p.id] = got_map.get(p.id, 0.0) + qty_in_puom

            ratios = []
            bom_qty = float(getattr(bom, "product_qty", 1.0) or 1.0)

            for bl in bom.bom_line_ids:
                needed_per_kit = float(bl.product_qty or 0.0) / bom_qty
                if not needed_per_kit:
                    ratios.append(0.0)
                    continue

                got_in_puom = got_map.get(bl.product_id.id, 0.0)
                got_in_bl_uom = to_uom(got_in_puom, bl.product_id.uom_id, bl.product_uom_id)
                ratios.append(got_in_bl_uom / needed_per_kit)

            kit_qty_bom_uom = min(ratios) if ratios else 0.0
            if not kit_qty_bom_uom or kit_qty_bom_uom <= 0:
                return ""

            kit_qty_sale_uom = to_uom(kit_qty_bom_uom, bom_uom, sale_uom)
            return kit_qty_sale_uom if kit_qty_sale_uom > 0 else ""

        # -------------------------
        # Collect moves
        # -------------------------
        moves = self.move_ids_without_package.filtered(
            lambda m: m.state != "cancel" and m.product_id
        )

        # sale moves: must have sale_line_id
        sale_moves = moves.filtered(lambda m: m.sale_line_id and m.sale_line_id.product_uom_qty > 0)

        # Component moves ONLY if kit_component AND sale_line_id exists
        comp_moves = sale_moves.filtered(lambda m: is_kit_component(m))

        # Normal sale moves = not component BUT still have sale_line_id
        normal_sale_moves = sale_moves.filtered(lambda m: not is_kit_component(m))

        # Material Tambahan = NO sale_line_id (includes orphan kit_component)
        material_moves = moves.filtered(lambda m: not m.sale_line_id)

        StockMove = self.env["stock.move"]

        comp_by_sl = {}
        for m in comp_moves:
            sl = m.sale_line_id
            comp_by_sl.setdefault(sl.id, {"sl": sl, "moves": StockMove})
            comp_by_sl[sl.id]["moves"] |= m

        normal_by_sl = {}
        for m in normal_sale_moves:
            sl = m.sale_line_id
            normal_by_sl.setdefault(sl.id, {"sl": sl, "moves": StockMove})
            normal_by_sl[sl.id]["moves"] |= m

        lines = []

        # -------------------------
        # Build ordered sale lines (sale.order_line order + leftovers)
        # -------------------------
        sale = getattr(self, "sale_id", False)
        move_sls = sale_moves.mapped("sale_line_id")

        ordered_sls = self.env["sale.order.line"]
        if sale and getattr(sale, "order_line", False):
            ordered_sls = sale.order_line.filtered(lambda sl: sl in move_sls)

            leftovers = (move_sls - sale.order_line)
            if leftovers:
                ordered_sls |= leftovers.sorted(key=lambda sl: (sl.sequence, sl.id))
        else:
            ordered_sls = move_sls.sorted(key=lambda sl: (sl.sequence, sl.id))

        # -------------------------
        # 1) Print sale lines
        # -------------------------
        for sl in ordered_sls:
            sl_comp = comp_by_sl.get(sl.id, {}).get("moves", StockMove)
            sl_norm = normal_by_sl.get(sl.id, {}).get("moves", StockMove)

            sale_uom = sl.product_uom or sl.product_id.uom_id

            # KIT sale line
            if sl_comp:
                # qty: prefer normal moves qty if exist else bom compute
                if sl_norm:
                    norm_map = sum_moves_by_product(sl_norm, target_uom_getter=lambda p, u=sale_uom: u)
                    kit_qty = sum(v["qty"] for v in norm_map.values()) if norm_map else 0.0
                    kit_qty = kit_qty
                    # description: from a normal move description_picking if available
                    rep_move = next(iter(sl_norm), False)
                    main_desc = move_desc(rep_move, sl.name)
                else:
                    kit_qty = compute_kit_qty_from_bom(sl_comp, sale_uom)
                    rep_move = next(iter(sl_comp), False)
                    main_desc = move_desc(rep_move, sl.name)

                add_main(
                    main_desc,
                    code=sl.product_id.default_code,
                    qty=kit_qty,
                    uom=sale_uom.name,
                )

                # component sub lines (description from move.description_picking)
                comp_map = sum_moves_by_product(sl_comp)
                for pid in sorted(comp_map.keys(), key=lambda k: comp_map[k]["product"].name or ""):
                    p = comp_map[pid]["product"]
                    desc = comp_map[pid]["desc"] or move_desc(comp_map[pid]["move"], p.name)
                    add_sub(
                        desc,
                        code=p.default_code,
                        qty=comp_map[pid]["qty"],
                        uom=comp_map[pid]["uom"].name,
                    )
                continue

            # NORMAL sale line
            if sl_norm:
                # group qty by product, and pick a representative move for description_picking
                norm_map = sum_moves_by_product(sl_norm, target_uom_getter=lambda p, u=sale_uom: u)
                qty = sum(v["qty"] for v in norm_map.values()) if norm_map else 0.0

                # description from the representative move's description_picking (fallback to sl.name)
                rep_move = next(iter(sl_norm), False)
                main_desc = move_desc(rep_move, sl.name)

                add_main(
                    main_desc,
                    code=sl.product_id.default_code,
                    qty=qty,
                    uom=sale_uom.name,
                )

        # -------------------------
        # 2) MATERIAL TAMBAHAN
        # -------------------------
        if material_moves:
            add_main("MATERIAL TAMBAHAN", is_section_header=True)

            mt_map = sum_moves_by_product(material_moves)
            for pid in sorted(mt_map.keys(), key=lambda k: mt_map[k]["product"].name or ""):
                p = mt_map[pid]["product"]
                desc = mt_map[pid]["desc"] or move_desc(mt_map[pid]["move"], p.name)
                add_sub(
                    desc,
                    code=p.default_code,
                    qty=mt_map[pid]["qty"],
                    uom=mt_map[pid]["uom"].name,
                )

        return lines




    def print_7energi_delivery_order(self):
        self.ensure_one()
        return self.env.ref('7energi_custom_inventory.action_report_7energi_delivery_order').report_action(self)