# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
from openerp.osv import fields, osv
from openerp.osv.orm import except_orm

class gym_member(osv.osv):
    _name = 'gym.member'
    _columns = {
        'name': fields.char('Tên thành viên', size=50, required=True),
        'phone': fields.char('Số điện thoại', size=20, required=True),
        'email': fields.char('Email', size=100),
        'gender': fields.selection([('male', 'Nam'), ('female', 'Nữ')], 'Giới tính', required=True),
        'address': fields.char('Địa chỉ', size=255),
        'join_date': fields.date('Ngày tham gia'),
        'state': fields.selection([('accepted', 'Cho phép'), ('blocked', 'Khóa')], 'Trạng thái', required=True),
        'membership_ids': fields.one2many('gym.membership', 'member_id', 'Memberships'),
    }

    _defaults = {
        'gender': 'male',
        'join_date': fields.date.context_today,
        'state': 'accepted'
    }

    _sql_constraints = [
        ('email_unique', 'unique(email)', 'Email đã tồn tại!'),
        ('phone_unique', 'unique(phone)', 'Số điện thoại đã tồn tại!'),
    ]

    def action_view_memberships(self, cr, uid, ids, context=None):
        member_id = ids[0] if ids else False
        mod_obj = self.pool.get('ir.model.data')
        try:
            tree_view_id = mod_obj.get_object_reference(cr, uid, 'gym_management', 'view_membership_tree')[1]
            form_view_id = mod_obj.get_object_reference(cr, uid, 'gym_management', 'view_membership_form')[1]
        except ValueError:
            tree_view_id = False
            form_view_id = False

        return {
            'name': 'Các gói tập đã đăng ký',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'gym.membership',
            'type': 'ir.actions.act_window',
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
            'domain': [('member_id', '=', member_id)],
            'context': {'default_member_id': member_id},
        }

gym_member()

class gym_membership(osv.osv):
    _name = 'gym.membership'
    _columns = {
        'member_id': fields.many2one('gym.member', 'Thành viên', required=True),
        'package_id': fields.many2one('gym.package', 'Gói tập', required=True),
        'trainer_id': fields.many2one('gym.trainer', 'Huấn luyện viên'),
        'start_date': fields.date('Ngày bắt đầu'),
        'end_date': fields.date('Ngày kết thúc'),
        'total_amount': fields.float('Tổng tiền', digits=(16, 2)),
        'payment_status': fields.selection([('unpaid', 'Chưa thanh toán'), ('paid', 'Đã thanh toán')], 'Thanh toán', required=True),
        'status': fields.selection([('active', 'Kích hoạt'), ('expired', 'Hết hạn'), ('canceled', 'Đã hủy')], 'Trạng thái', required=True),
    }

    _defaults = {
        'start_date': fields.date.context_today,
        'end_date': fields.date.context_today,
        'total_amount': 0.0,
        'status': 'active',
        'payment_status': 'unpaid',
    }

    def onchange_package_id(self, cr, uid, ids, package_id, context=None):
        result = {'value': {}}
        if package_id:
            package = self.pool.get('gym.package').browse(cr, uid, package_id, context=context)
            today = datetime.date.today()
            end_date = today + datetime.timedelta(days=package.duration_days)
            result['value'].update({
                'start_date': today.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'total_amount': package.price,
            })
        return result

    def _check_dates(self, start_date, end_date):
        if start_date and end_date:
            start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
            if end < start:
                raise except_orm(u'Lỗi ngày', u'Ngày kết thúc phải lớn hơn hoặc bằng ngày bắt đầu.')

    def _is_admin(self, cr, uid, context=None):
        user_obj = self.pool.get('res.users')
        return uid == 1 or user_obj.has_group(cr, uid, 'base.group_system', context=context)

    def _validate_status_payment(self, cr, uid, vals, membership=None, context=None):
        status = vals.get('status') if vals.get('status') is not None else (membership.status if membership else None)
        payment_status = vals.get('payment_status') if vals.get('payment_status') is not None else (membership.payment_status if membership else None)

        if status == 'canceled' and not self._is_admin(cr, uid, context=context):
            raise except_orm(u'Lỗi phân quyền', u'Chỉ quản trị viên mới được hủy gói tập.')

        if status == 'expired' and not (context or {}).get('force_expire'):
            raise except_orm(u'Lỗi trạng thái', u'Không thể thực hiện!.')

        if status == 'active' and payment_status != 'paid':
            raise except_orm(u'Lỗi trạng thái', u'Gói tập chưa được thanh toán.')

        if payment_status == 'unpaid' and status == 'active':
            raise except_orm(u'Lỗi trạng thái', u'Gói tập chưa được thanh toán.')

    def create(self, cr, uid, vals, context=None):
        if vals.get('member_id'):
            member = self.pool.get('gym.member').browse(cr, uid, vals['member_id'], context=context)
            if member.state == 'blocked':
                raise except_orm(u'Lỗi đăng ký gói!', u'Thành viên đang bị khóa, không thể đăng ký gói tập.')
        if vals.get('trainer_id'):
            trainer = self.pool.get('gym.trainer').browse(cr, uid, vals['trainer_id'], context=context)
            if not trainer.active:
                raise except_orm(u'Lỗi đăng ký gói!', u'Huấn luyện viên đã nghỉ hưu hoặc không còn hoạt động, vui lòng chọn huấn luyện viên khác.')
        if vals.get('package_id'):
            package = self.pool.get('gym.package').browse(cr, uid, vals['package_id'], context=context)
            today = datetime.date.today()
            if not vals.get('start_date'):
                vals['start_date'] = today.strftime('%Y-%m-%d')
            if not vals.get('end_date'):
                end_date = today + datetime.timedelta(days=(package.duration_days or 0))
                vals['end_date'] = end_date.strftime('%Y-%m-%d')
            if not vals.get('total_amount'):
                vals['total_amount'] = package.price or 0.0
        self._check_dates(vals.get('start_date'), vals.get('end_date'))
        self._validate_status_payment(cr, uid, vals, context=context)
        return super(gym_membership, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('package_id'):
            package = self.pool.get('gym.package').browse(cr, uid, vals['package_id'], context=context)
            today = datetime.date.today()
            if not vals.get('start_date'):
                vals['start_date'] = today.strftime('%Y-%m-%d')
            if not vals.get('end_date'):
                end_date = today + datetime.timedelta(days=(package.duration_days or 0))
                vals['end_date'] = end_date.strftime('%Y-%m-%d')
            if not vals.get('total_amount'):
                vals['total_amount'] = package.price or 0.0
        if vals.get('start_date') or vals.get('end_date'):
            for membership in self.browse(cr, uid, ids, context=context):
                start_date = vals.get('start_date') or membership.start_date
                end_date = vals.get('end_date') or membership.end_date
                self._check_dates(start_date, end_date)
        for membership in self.browse(cr, uid, ids, context=context):
            self._validate_status_payment(cr, uid, vals, membership=membership, context=context)
        return super(gym_membership, self).write(cr, uid, ids, vals, context=context)

    def cron_expire_memberships(self, cr, uid, context=None):
        """Cron job: set membership status to 'expired' when end_date is before today."""
        today = datetime.date.today().strftime('%Y-%m-%d')
        membership_ids = self.search(cr, uid, [
            ('status', '=', 'active'),
            ('end_date', '<', today),
        ])
        if membership_ids:
            self.write(cr, uid, membership_ids, {'status': 'expired'}, context=dict(context or {}, force_expire=True))
        return True

gym_membership()

class gym_trainer(osv.osv):
    _name = 'gym.trainer'
    _columns = {
        'name': fields.char('Tên huấn luyện viên', size=64, required=True),
        'phone': fields.char('Số điện thoại', size=20),
        'email': fields.char('Email', size=100),
        'specialty': fields.char('Chuyên môn', size=64),
        'hire_date': fields.date('Ngày bắt đầu'),
        'active': fields.boolean('Hoạt động'),
        'membership_ids': fields.one2many('gym.membership', 'trainer_id', 'Memberships'),
    }

    _defaults = {
        'hire_date': fields.date.context_today,
        'active': True,
    }

gym_trainer()

class gym_package(osv.osv):
    _name = 'gym.package'
    _columns = {
        'name': fields.char('Tên gói tập', required=True),
        'price': fields.float('Giá', digits=(16, 2), required=True),
        'duration_days': fields.integer('Số ngày', required=True),
        'description': fields.text('Mô tả'),
        'membership_ids': fields.one2many('gym.membership', 'package_id', 'Memberships'),
        'active': fields.boolean('Hoạt động'),
    }

    _defaults = {
        'active': True
    }

    def _validate_package_values(self, vals):
        if 'price' in vals and vals.get('price') is not None and vals['price'] < 0:
            raise except_orm(u'Lỗi giá', u'Giá gói tập không được phép là số âm.')
        if 'duration_days' in vals and vals.get('duration_days') is not None and vals['duration_days'] < 0:
            raise except_orm(u'Lỗi số ngày', u'Số ngày tập không được phép là số âm.')

    def create(self, cr, uid, vals, context=None):
        self._validate_package_values(vals)
        return super(gym_package, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        self._validate_package_values(vals)
        return super(gym_package, self).write(cr, uid, ids, vals, context=context)

gym_package()

class gym_checkin(osv.osv):
    _name = 'gym.checkin'
    _columns = {
        'member_id': fields.many2one('gym.member', 'Thành viên', required=True),
        'checkin_time': fields.datetime('Thời gian vào'),
        'checkout_time': fields.datetime('Thời gian ra'),
    }

    _defaults = {
        'checkin_time': fields.datetime.now,
    }

    def create(self, cr, uid, vals, context=None):
        member_obj = self.pool.get('gym.member')
        membership_obj = self.pool.get('gym.membership')
        member_id = vals.get('member_id')

        if not member_id:
            raise except_orm(u'Lỗi!', u'Vui lòng chọn thành viên!')

        member_ids = member_obj.search(cr, uid, [('id', '=', member_id)])
        if not member_ids:
            raise except_orm(u'Lỗi!', u'Thành viên không tồn tại!')

        member = member_obj.browse(cr, uid, member_id, context=context)
        if member.state == 'blocked':
            raise except_orm(u'Từ chối check-in!', u'Thành viên đang bị khóa!')

        today = datetime.date.today().strftime('%Y-%m-%d')
        membership_ids = membership_obj.search(cr, uid, [
            ('member_id', '=', member_id),
            ('status', '=', 'active'),
            ('payment_status', '=', 'paid'),
            ('start_date', '<=', today),
            ('end_date', '>=', today)
        ])
        if not membership_ids:
            raise except_orm(u'Từ chối check-in!', u'Không có gói tập hợp lệ, chưa đến ngày tập hoặc đã hết hạn!')

        membership_ids = membership_obj.search(cr, uid, [
            ('member_id', '=', member_id),
            ('status', '=', 'active'),
            ('payment_status', '=', 'paid'),
            ('end_date', '>=', today)
        ])
        if not membership_ids:
            raise except_orm(u'Từ chối check-in!', u'Không có gói tập hợp lệ hoặc đã hết hạn!')

        membership = membership_obj.browse(cr, uid, membership_ids[0], context=context)
        if not membership.package_id:
            raise except_orm(u'Lỗi dữ liệu!', u'Membership chưa có gói tập!')

        if not membership.package_id.active:
            raise except_orm(u'Từ chối check-in!', u'Gói tập hiện đang ngừng hoạt động!')

        duplicate_ids = self.search(cr, uid, [
            ('member_id', '=', member_id),
            ('checkout_time', '=', False)
        ])
        if duplicate_ids:
            raise except_orm(u'Từ chối check-in!', u'Thành viên đang ở trong phòng tập!')

        if not vals.get('checkin_time'):
            vals['checkin_time'] = fields.datetime.now()

        return super(gym_checkin, self).create(cr, uid, vals, context=context)

    def action_checkout(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'checkout_time': fields.datetime.now(),
            'status': 'checked_out'
        })
        return True

gym_checkin()