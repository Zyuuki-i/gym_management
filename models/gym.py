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

    def create(self, cr, uid, vals, context=None):
        if vals.get('member_id'):
            member = self.pool.get('gym.member').browse(cr, uid, vals['member_id'], context=context)
            if member.state == 'blocked':
                raise except_orm(u'Lỗi đăng ký gói!', u'Thành viên đang bị khóa, không thể đăng ký gói tập.')
        if vals.get('trainer_id'):
            trainer = self.pool.get('gym.trainer').browse(cr, uid, vals['trainer_id'], context=context)
            if not trainer.active:
                raise except_orm(u'Lỗi đăng ký gói!', u'Huấn luyện viên đã nghỉ hưu hoặc không còn hoạt động, vui lòng chọn huấn luyện viên khác.')
        return super(gym_membership, self).create(cr, uid, vals, context=context)

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
        'price': fields.float('Giá', digits=(16, 2)),
        'duration_days': fields.integer('Số ngày'),
        'description': fields.text('Mô tả'),
        'membership_ids': fields.one2many('gym.membership', 'package_id', 'Memberships'),
        'active': fields.boolean('Hoạt động'),
    }

    _defaults = {
        'active': True
    }

    _sql_constraints = [
        ('package_id_unique', 'unique(package_id)', 'Mã gói tập đã tồn tại!')
    ]

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